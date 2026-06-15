#!/usr/bin/env python3
"""HotRadar - 国内热点监控主入口

抓取微博/知乎/抖音热榜，输出到：
1. 本地文件（JSON + SMCC Markdown）
2. SMCC 项目原料库
3. 飞书群通知（含完整热点内容）
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


def save_output(data: List[Dict], output_dir: Path) -> Path:
    """保存 JSON 到指定目录"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    output_file = output_dir / f"{today}.json"

    # 如果文件已存在，先读取并合并
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
    """生成 SMCC 标准格式的热点速览 markdown 内容"""
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    lines = [f"# 热点速览 — {today} {now}\n"]

    platform_names = {
        "weibo": "微博",
        "douyin": "抖音",
        "zhihu": "知乎",
        "xiaohongshu": "小红书",
    }

    # 按平台分组
    platforms_dict = {}
    for item in data:
        p = item["platform"]
        if p not in platforms_dict:
            platforms_dict[p] = []
        platforms_dict[p].append(item)

    for platform_key in ["weibo", "douyin", "zhihu", "xiaohongshu"]:
        if platform_key not in platforms_dict:
            continue
        items = platforms_dict[platform_key]
        items.sort(key=lambda x: x["rank"])

        lines.append(f"## {platform_names.get(platform_key, platform_key)}\n")
        lines.append("| 排名 | 标题 | 热度 |")
        lines.append("|:---:|------|------|")

        for item in items[:10]:
            title = item["title"].replace("|", "\\|")
            heat = item.get("heat", "")
            lines.append(f"| {item['rank']} | {title} | {heat} |")
        lines.append("\n")

    return "\n".join(lines)


def save_smcc_file(content: str, output_dir: Path) -> Path:
    """保存 SMCC Markdown 文件"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = output_dir / f"{today}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    return output_file


def send_to_feishu(content: str, logger) -> bool:
    """通过 lark-cli 发送热点速览到飞书群"""
    try:
        result = subprocess.run(
            ["lark-cli", "im", "+messages-send",
             "--chat-id", FEISHU_CHAT_ID,
             "--markdown", content],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            logger.info("飞书消息发送成功")
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
                        help="指定平台，逗号分隔 (weibo,douyin,zhihu)")
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

    # 解析平台
    platform_map = {
        "weibo": "tophub",
        "douyin": "tophub",
        "zhihu": "tophub",
        "xiaohongshu": "xhs",
    }

    if args.platform:
        selected = [p.strip() for p in args.platform.split(",")]
    else:
        selected = list(platform_map.keys())

    tophub_selected = [p for p in selected if platform_map.get(p) == "tophub"]
    xhs_selected = [p for p in selected if platform_map.get(p) == "xhs"]

    all_data = []

    # 1) tophub 平台：一次浏览器渲染抓所有
    if tophub_selected:
        spider = TophubSpider(logger, platforms=tophub_selected)
        try:
            items = spider.fetch()
            for item in items:
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
    for platform_key in xhs_selected:
        try:
            spider = XiaoHongShuSpider(logger)
            items = spider.fetch()
            for item in items:
                all_data.append({
                    "platform": item.platform,
                    "title": item.title,
                    "rank": item.rank,
                    "heat": item.heat,
                    "url": item.url,
                    "fetched_at": item.fetched_at,
                })
        except Exception as e:
            logger.error(f"{platform_key} 抓取失败: {e}")

    if not all_data:
        logger.error("未抓取到任何数据")
        return 1

    logger.info(f"共抓取 {len(all_data)} 条热点数据")

    # === 输出 ===
    output_dir = Path(args.output)

    # 1) JSON
    if args.format in ("json", "all"):
        json_file = save_output(all_data, output_dir)
        logger.info(f"JSON 输出: {json_file}")

    # 2) SMCC Markdown
    if args.format in ("smcc", "all"):
        smcc_content = export_smcc_content(all_data)

        # 保存到输出目录
        f1 = save_smcc_file(smcc_content, output_dir / "smcc")
        logger.info(f"SMCC 输出: {f1}")

        # 保存到 SMCC 项目原料库
        if not args.no_smcc and SMCC_RAW_DIR.exists():
            f2 = save_smcc_file(smcc_content, SMCC_RAW_DIR)
            logger.info(f"原料库: {f2}")

        # 发送到飞书
        if not args.no_feishu:
            send_to_feishu(smcc_content, logger)

    return 0


if __name__ == "__main__":
    sys.exit(main())
