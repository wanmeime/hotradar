"""知乎热榜抓取"""
import json
import re
from datetime import datetime

from scrapling import Fetcher

from .base import BaseSpider, HotItem


class ZhihuSpider(BaseSpider):
    """知乎热榜"""

    name = "知乎热榜"
    platform = "zhihu"

    def fetch(self):
        self.logger.info("开始抓取知乎热榜...")
        fetched_at = datetime.now().isoformat()

        try:
            page = Fetcher.get("https://www.zhihu.com/hot", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,*/*;q=0.9",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://www.zhihu.com/hot",
            })
            items = self._parse(page.text, fetched_at)
            if items:
                return items
        except Exception as e:
            self.logger.error(f"知乎：页面抓取失败 {e}")

        # 第二层：API
        try:
            return self._fetch_api(fetched_at)
        except Exception as e:
            self.logger.error(f"知乎：API 抓取失败 {e}")

        return []

    def _parse(self, html, fetched_at):
        """解析知乎热榜 HTML 中的初始数据"""
        items = []
        # 知乎 SSR 数据
        init_data_match = re.search(r'<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.*?})</script>', html, re.DOTALL)
        if init_data_match:
            try:
                data = json.loads(init_data_match.group(1))
                for item in data.get("hot", []):
                    items.append(HotItem(
                        platform="zhihu",
                        title=item.get("target", {}).get("title", "").strip(),
                        rank=len(items) + 1,
                        heat=str(item.get("detail_text", "")),
                        url=item.get("target", {}).get("url", ""),
                        fetched_at=fetched_at,
                    ))
                return items
            except (json.JSONDecodeError, KeyError):
                pass

        # DOM 兜底
        titles = re.findall(r'<h2[^>]*class="HotItem-title"[^>]*>([^<]+)', html)
        heats = re.findall(r'>([\d.]+万?热度)<', html)
        for i, (t, h) in enumerate(zip(titles, heats), 1):
            items.append(HotItem(
                platform="zhihu",
                title=t.strip(),
                rank=i,
                heat=h.strip(),
                url="",
                fetched_at=fetched_at,
            ))
        return items

    def _fetch_api(self, fetched_at):
        """知乎 API 兜底"""
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists?limit=50"
        try:
            resp = Fetcher.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Referer": "https://www.zhihu.com/hot",
            })
            data = resp.json()
            items = []
            for i, item in enumerate(data.get("data", []), 1):
                target = item.get("target", {})
                items.append(HotItem(
                    platform="zhihu",
                    title=target.get("title", "").strip(),
                    rank=i,
                    heat=str(item.get("detail_text", "")),
                    url=target.get("url", ""),
                    fetched_at=fetched_at,
                ))
            return items
        except Exception as e:
            self.logger.error(f"知乎 API 解析失败: {e}")
            return []
