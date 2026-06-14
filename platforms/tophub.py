"""tophub.today 聚合数据爬虫 - 统一获取微博/知乎/抖音热点"""
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from .base import BaseSpider, HotItem


class TophubSpider(BaseSpider):
    """基于 tophub.today 的多平台热点爬虫

    页面结构：一个 section 包含 3 个连续行：
      行1: 平台名（微博/知乎/抖音）
      行2: 区段名（热搜榜/热榜/总榜）
      行3: 空行
      行4+: 编号列表（序号/标题/热度 交替出现）
      结尾: "X分钟前" → 下一个平台
    """

    SECTIONS = [
        ("微博", "热搜榜", "weibo"),
        ("知乎", "热榜", "zhihu"),
        ("抖音", "总榜", "douyin"),
    ]

    def __init__(self, logger, platforms=None):
        super().__init__(logger)
        self._platforms = set(platforms or ["weibo", "zhihu", "douyin"])

    def fetch(self) -> list:
        """渲染首页一次，提取所有平台数据"""
        self.logger.info(f"从 tophub.today 抓取: {', '.join(sorted(self._platforms))}")
        fetched_at = datetime.now().isoformat()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://tophub.today/", wait_until="networkidle")
                page.wait_for_timeout(5000)
                lines = page.inner_text("body").split("\n")
                browser.close()
        except Exception as e:
            self.logger.error(f"Playwright 渲染失败: {e}")
            return []

        # 解析所有区段
        all_items = []
        for platform_name, section_name, pid in self.SECTIONS:
            if pid not in self._platforms:
                continue
            items = self._extract_section(lines, platform_name, section_name, pid, fetched_at)
            self.logger.info(f"  {platform_name}{section_name}: {len(items)} 条")
            all_items.extend(items)

        return all_items

    def _extract_section(self, lines, platform_name, section_name, platform_id, fetched_at):
        """从行列表中提取指定平台的区段"""
        # 找到数据区段（而非导航区段）：
        # 导航区段后是空行，数据区段后紧接数字条目
        start_line = None
        for i in range(len(lines) - 2):
            if (lines[i].strip() == platform_name
                    and lines[i + 1].strip() == section_name
                    and lines[i + 2].strip().isdigit()):
                start_line = i + 2
                break

        if start_line is None:
            self.logger.warning(f"  未找到 [{platform_name} {section_name}]")
            return []

        # 从 start_line 往后找编号数据，直到遇到时间标记或下一个平台名
        items = []
        # 收集平台名集合（用于判断结束）
        platform_names = {p for p, _, _ in self.SECTIONS}

        i = start_line
        while i < len(lines) and len(items) < 10:
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # 结束条件：遇到时间标记（"X分钟前"）
            if re.match(r'^\d+分钟前$', line):
                break

            # 结束条件：遇到下一个平台名
            if line in platform_names:
                break

            # 尝试解析编号行
            if line.isdigit():
                rank = int(line)
                i += 1

                # 标题行
                title = lines[i].strip() if i < len(lines) else ""
                i += 1

                # 热度行
                heat = lines[i].strip() if i < len(lines) else ""
                i += 1

                if title and not title.isdigit():
                    items.append(HotItem(
                        platform=platform_id,
                        title=title,
                        rank=rank,
                        heat=heat,
                        url="",
                        fetched_at=fetched_at,
                    ))
            else:
                i += 1

        return items[:10]
