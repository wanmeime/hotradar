"""小红书热点爬虫"""
from datetime import datetime
from .base import BaseSpider, HotItem


class XiaoHongShuSpider(BaseSpider):
    """小红书热点爬虫

    小红书反爬极严（Cloudflare + IP 封锁 + 需登录态）。
    当前 WSL 环境 IP 已被封锁，无法稳定获取数据。

    如需绕过：
    1. 使用 Playwright 连接 Windows 上已登录小红书的 Chrome
    2. 或使用 tophub.today 等第三方聚合平台（目前不收录小红书）
    3. 或参考 easyclaw 的 xiaohongshu-search skill（browser-use + 登录态）
    """

    name = "小红书热点"
    platform = "xiaohongshu"

    def fetch(self):
        self.logger.warning(
            "小红书：反爬机制严苛，当前环境 IP 已被封锁，暂无法抓取。"
        )
        return []
