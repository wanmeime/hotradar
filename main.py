#!/usr/bin/env python3
"""HotRadar - 国内热点监控主入口"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from config import setup_logging, PLATFORMS
from platforms import TophubSpider, XiaoHongShuSpider


def save_output(data: List[Dict], output_dir: Path):
    """保存输出到指定目录"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 按日期文件名保存
    today = datetime.now().strftime("%Y%m%d")
    output_file = output_dir / f"{today}.json"

    # 如果文件已存在，先读取并合并
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # 去重：新数据覆盖旧数据
        existing_titles = {(item["platform"], item["title"]) for item in existing}
        for item in data:
            key = (item["platform"], item["title"])
            if key in existing_titles:
                # 更新现有条目
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


def export_smcc_format(data: List[Dict], output_dir: Path) -> Path:
    """导出 SMCC 标准格式的热点速览 markdown"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    output_file = output_dir / f"{today}.md"

    # 按平台分组
    platforms_dict = {}
    for item in data:
        platform = item["platform"]
        if platform not in platforms_dict:
            platforms_dict[platform] = []
        platforms_dict[platform].append(item)

    # 生成 markdown
    lines = [f"# 热点速览 — {today} {datetime.now().strftime('%H:%M')}\n"]

    platform_names = {
        "weibo": "微博",
        "douyin": "抖音",
        "zhihu": "知乎",
        "xiaohongshu": "小红书",
    }

    for platform_key in ["weibo", "douyin", "zhihu", "xiaohongshu"]:
        if platform_key not in platforms_dict:
            continue

        items = platforms_dict[platform_key]
        items.sort(key=lambda x: x["rank"])

        lines.append(f"## {platform_names.get(platform_key, platform_key)}\n")
        lines.append("| 排名 | 标题 | 热度 |")
        lines.append("|:---:|------|------|")

        for item in items[:10]:  # 只取前10
            title = item["title"].replace("|", "\\|")
            heat = item.get("heat", "")
            rank = item["rank"]
            lines.append(f"| {rank} | {title} | {heat} |")

        lines.append("\n")

    # 保存
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_file


def main():
    parser = argparse.ArgumentParser(description="HotRadar - 国内热点监控")
    parser.add_argument("--platform", "-p", help="指定平台，逗号分隔 (weibo,douyin,zhihu,xiaohongshu)")
    parser.add_argument("--output", "-o", default="output", help="输出目录 (默认: output/)")
    parser.add_argument("--format", choices=["json", "smcc", "all"], default="all",
                        help="输出格式: json(原始数据), smcc(标准markdown), all(两者)")
    args = parser.parse_args()

    logger = setup_logging()

    # 解析平台
    TOPHUB_PLATFORMS = ["weibo", "douyin", "zhihu"]
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

    # 分类：tophub 平台合并为一次渲染，小红书单独处理
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

    # 输出
    output_dir = Path(args.output)

    if args.format in ("json", "all"):
        json_file = save_output(all_data, output_dir)
        logger.info(f"JSON 输出: {json_file}")

    if args.format in ("smcc", "all"):
        md_file = export_smcc_format(all_data, output_dir / "smcc")
        logger.info(f"SMCC 输出: {md_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
