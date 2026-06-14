"""微博热搜抓取"""
from datetime import datetime

from scrapling import Fetcher

from .base import BaseSpider, HotItem


class WeiboSpider(BaseSpider):
    """微博热搜"""

    name = "微博热搜"
    platform = "weibo"

    def fetch(self):
        self.logger.info("开始抓取微博热搜...")

        url = "https://s.weibo.com/top/summary?cate=realtimehot"
        page = Fetcher.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://s.weibo.com/",
        })

        items = []
        fetched_at = datetime.now().isoformat()

        # 热搜表格行
        rows = page.css("#pl_top_realtimehot tbody tr")
        if not rows:
            self.logger.warning("微博：未找到热搜数据")
            return items

        for row in rows:
            try:
                rank_el = row.css_first("td.ranktop")
                if not rank_el:
                    continue
                rank = int(rank_el.text.strip())

                title_el = row.css_first("td.td-02 a")
                if not title_el:
                    continue
                title = title_el.text.strip()
                detail_url = "https:" + title_el.get("href", "")

                heat_el = row.css_first("td.td-02 i")
                heat = heat_el.text.strip() if heat_el else "0"

                items.append(HotItem(
                    platform="weibo",
                    title=title,
                    rank=rank,
                    heat=heat,
                    url=detail_url,
                    fetched_at=fetched_at,
                ))
            except (ValueError, AttributeError) as e:
                self.logger.debug(f"微博：跳过异常行 {e}")
                continue

        self.logger.info(f"微博热搜抓取完成: {len(items)}条")
        return items

