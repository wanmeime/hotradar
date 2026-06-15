#!/usr/bin/env python3
"""HotRadar - 国内热点监控主入口

抓取微博/知乎/抖音热榜，输出到：
1. 本地文件（JSON + SMCC Markdown）
2. SMCC 项目原料库
3. 飞书群卡片消息
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from config import setup_logging
from platforms import TophubSpider, XiaoHongShuSpider

# 飞书群配置
FEISHU_CHAT_ID = "oc_d2e8df3c676afa2c352d8ece0a9b6141"
# SMCC 原料库路径
SMCC_RAW_DIR = Path("/home/jiaod/smcc/00-原料/热点调研")
# 各平台中文名
PLATFORM_NAMES = {
    "weibo": "微博热搜榜",
    "douyin": "抖音总榜",
    "zhihu": "知乎热榜",
    "xiaohongshu": "小红书",
}


def save_output(data: List[Dict], output_dir: Path) -> Path:
    """保存 JSON 到指定目录"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    output_file = output_dir / f"{today}.json"

    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_titles = {(item["platform"], item["title"]) for item in existing}
        for item in data:
            key = (item["platform"], item["title"])
            if key in existing_titles:
                for i, existing_item in enumerate(existing):
                    if (existing_item["platform"], existing_item["title"]) == key:
                        existing[i] = item
                        break
            else:
                existing.append(item)
        data = existing

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return output_file


def export_smcc_content(data: List[Dict]) -> str:
    """生成 SMCC 标准格式 Markdown（带表格，用于文件存档）"""
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")
    lines = [f"# 热点速览 — {today} {now}\n"]

    by_platform = _group_by_platform(data)

    for pk in ["weibo", "douyin", "zhihu", "xiaohongshu"]:
        if pk not in by_platform:
            continue
        items = sorted(by_platform[pk], key=lambda x: x["rank"])
        lines.append(f"## {PLATFORM_NAMES.get(pk, pk)}\n")
        lines.append("| 排名 | 标题 | 热度 |")
        lines.append("|:---:|------|------|")
        for item in items[:10]:
            title = item["title"].replace("|", "\\|")
            heat = item.get("heat", "")
            lines.append(f"| {item['rank']} | {title} | {heat} |")
        lines.append("")

    return "\n".join(lines)


def save_smcc_file(content: str, output_dir: Path) -> Path:
    """保存 Markdown 文件"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out = output_dir / f"{today}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    return out


def _group_by_platform(data: List[Dict]) -> Dict[str, list]:
    """按平台分组"""
    grouped = {}
    for item in data:
        grouped.setdefault(item["platform"], []).append(item)
    return grouped


def build_feishu_card(data: List[Dict]) -> str:
    """构建飞书卡片消息 JSON

    卡片结构：
    - header: 标题 + 时间
    - 每个平台一个 markdown 区块，用分割线隔开
    """
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    elements = []
    by_platform = _group_by_platform(data)
    first = True

    for pk in ["weibo", "douyin", "zhihu", "xiaohongshu"]:
        if pk not in by_platform:
            continue
        items = sorted(by_platform[pk], key=lambda x: x["rank"])

        # 分隔线（第一个平台前不画）
        if not first:
            elements.append({"tag": "hr"})
        first = False

        # 平台标题行
        name = PLATFORM_NAMES.get(pk, pk)
        platform_header = f"**{name}**"

        # 前 10 条热点
        item_lines = []
        for item in items[:10]:
            heat = item.get("heat", "")
            heat_str = f"  `{heat}`" if heat else ""
            # 标题中的特殊字符转义
            title = item["title"].replace("*", "\\*").replace("`", "\\`")
            item_lines.append(f"{item['rank']}. {title}{heat_str}")

        md_content = platform_header + "\n" + "\n".join(item_lines)

        elements.append({
            "tag": "markdown",
            "content": md_content,
        })

    # 底部提示
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{
            "tag": "plain_text",
            "content": f"🤖 HotRadar 自动抓取 · {today} {now}"
        }]
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"🔥 热点速览 — {today}"
            },
            "template": "blue",
        },
        "elements": elements,
    }

    return json.dumps(card, ensure_ascii=False)


def send_feishu_card(data: List[Dict], logger) -> bool:
    """发送飞书卡片消息"""
    card_json = build_feishu_card(data)
    try:
        result = subprocess.run(
            ["lark-cli", "im", "+messages-send",
             "--chat-id", FEISHU_CHAT_ID,
             "--msg-type", "interactive",
             "--content", card_json],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            logger.info("飞书卡片消息发送成功")
            return True
        else:
            logger.error(f"飞书发送失败: {result.stderr}")
            return False
    except FileNotFoundError:
        logger.error("lark-cli 未安装，无法发送飞书消息")
        return False
    except Exception as e:
        logger.error(f"飞书发送异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="HotRadar - 国内热点监控")
    parser.add_argument("--platform", "-p",
                        help="指定平台 (weibo,douyin,zhihu)")
    parser.add_argument("--output", "-o", default="output",
                        help="输出目录 (默认: output/)")
    parser.add_argument("--format", choices=["json", "smcc", "all"], default="all",
                        help="输出格式")
    parser.add_argument("--no-feishu", action="store_true",
                        help="不发送飞书消息")
    parser.add_argument("--no-smcc", action="store_true",
                        help="不存入 SMCC 原料库")
    args = parser.parse_args()

    logger = setup_logging()

    platform_map = {"weibo": "tophub", "douyin": "tophub",
                    "zhihu": "tophub", "xiaohongshu": "xhs"}

    if args.platform:
        selected = [p.strip() for p in args.platform.split(",")]
    else:
        selected = list(platform_map.keys())

    tophub_selected = [p for p in selected if platform_map[p] == "tophub"]
    xhs_selected = [p for p in selected if platform_map[p] == "xhs"]

    all_data = []

    # 1) tophub 平台：一次浏览器渲染抓所有
    if tophub_selected:
        spider = TophubSpider(logger, platforms=tophub_selected)
        try:
            for item in spider.fetch():
                all_data.append({
                    "platform": item.platform,
                    "title": item.title,
                    "rank": item.rank,
                    "heat": item.heat,
                    "url": item.url,
                    "fetched_at": item.fetched_at,
                })
        except Exception as e:
            logger.error(f"tophub 抓取失败: {e}")

    # 2) 小红书
    for _ in xhs_selected:
        try:
            for item in XiaoHongShuSpider(logger).fetch():
                all_data.append({
                    "platform": item.platform,
                    "title": item.title,
                    "rank": item.rank,
                    "heat": item.heat,
                    "url": item.url,
                    "fetched_at": item.fetched_at,
                })
        except Exception as e:
            logger.error(f"小红书抓取失败: {e}")

    if not all_data:
        logger.error("未抓取到任何数据")
        return 1

    logger.info(f"共抓取 {len(all_data)} 条热点数据")

    output_dir = Path(args.output)

    # JSON
    if args.format in ("json", "all"):
        f = save_output(all_data, output_dir)
        logger.info(f"JSON 输出: {f}")

    # SMCC Markdown
    if args.format in ("smcc", "all"):
        smcc = export_smcc_content(all_data)
        f1 = save_smcc_file(smcc, output_dir / "smcc")
        logger.info(f"SMCC 输出: {f1}")
        if not args.no_smcc and SMCC_RAW_DIR.exists():
            f2 = save_smcc_file(smcc, SMCC_RAW_DIR)
            logger.info(f"原料库: {f2}")

    # 飞书卡片
    if not args.no_feishu:
        send_feishu_card(all_data, logger)

    return 0


if __name__ == "__main__":
    sys.exit(main())
