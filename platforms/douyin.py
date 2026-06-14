"""抖音热榜抓取 - 参考 easyclaw 小红书 agent 的三层读取方案"""
import json
import re
from datetime import datetime

from scrapling import Fetcher

from .base import BaseSpider, HotItem


class DouyinSpider(BaseSpider):
    """抖音热搜"""

    name = "抖音热榜"
    platform = "douyin"

    def fetch(self):
        self.logger.info("开始抓取抖音热榜...")
        url = "https://www.douyin.com/hot"
        fetched_at = datetime.now().isoformat()

        try:
            page = Fetcher.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://www.douyin.com/",
                "Cookie": "__ac_nonce=",
            })
            items = self._parse(page.text, fetched_at)
            if items:
                return items
        except Exception as e:
            self.logger.error(f"抖音：第一层页面抓取失败 {e}")

        # 第二层：尝试 API
        try:
            return self._fetch_api(fetched_at)
        except Exception as e:
            self.logger.error(f"抖音：API 抓取失败 {e}")

        return []

    def _parse(self, html, fetched_at):
        """解析抖音热榜 HTML"""
        items = []
        # SSR 数据在 script 中
        pattern = re.search(r'<script[^>]*window\._SSR_HYDRATED_DATA\s*=\s*({.*?})</script>', html, re.DOTALL)
        if not pattern:
            # 新版页面可能没有 SSR_HYDRATED_DATA，尝试直接解析 DOM
            return self._parse_dom(html, fetched_at)

        try:
            data = json.loads(pattern.group(1))
            word_list = data.get("hotlist", {}).get("data", [])
            for item in word_list:
                items.append(HotItem(
                    platform="douyin",
                    title=item.get("word", "").strip(),
                    rank=len(items) + 1,
                    heat=str(item.get("hot_value", "")),
                    url=f"https://www.douyin.com/search/{item.get('word', '')}",
                    fetched_at=fetched_at,
                ))
        except (json.JSONDecodeError, KeyError):
            return self._parse_dom(html, fetched_at)

        return items

    def _parse_dom(self, html, fetched_at):
        """DOM 兜底解析"""
        items = []
        # 抖音热榜 DOM 结构
        titles = re.findall(r'data-e2e="hot-title">([^<]+)', html)
        heats = re.findall(r'data-e2e="hot-value">([^<]+)', html)
        for i, (t, h) in enumerate(zip(titles, heats), 1):
            items.append(HotItem(
                platform="douyin",
                title=t.strip(),
                rank=i,
                heat=h.strip(),
                url="",
                fetched_at=fetched_at,
            ))
        return items

    def _fetch_api(self, fetched_at):
        """API 兜底"""
        # 抖音没有公开稳定的 API，这里返回空
        self.logger.warning("抖音：API 暂无可用端点")
        return []
