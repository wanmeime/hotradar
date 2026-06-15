"""内容抓取模块 — 为写作 Agent 提供正文素材

核心能力：给定 URL，提取正文内容，输出结构化 Markdown。

使用方式：
    from platforms.content import extract_from_url, ContentFetcher

    # 方式1：直接提取 URL
    md = extract_from_url("https://news.sina.com.cn/xxx", logger)

    # 方式2：通过 ContentFetcher
    fetcher = ContentFetcher(logger)
    md = fetcher.fetch(url="https://...")
"""
from datetime import datetime
from urllib.parse import urlparse

import trafilatura
from scrapling.fetchers import Fetcher
from playwright.sync_api import sync_playwright

from .base import BaseSpider, HotItem


def _download(url: str, timeout: int = 20) -> str:
    """用 Scrapling 下载 URL 内容

    Scrapling 比 requests 多了 stealthy_headers、浏览器指纹伪装等反爬能力。
    """
    try:
        page = Fetcher.get(url, timeout=timeout, follow_redirects=True)
        if page.status == 200 and len(page.text) > 100:
            return page.text
    except Exception:
        pass
    return ""


def extract_from_url(url: str, logger=None) -> str:
    """从 URL 提取正文，返回 Markdown 格式素材文档

    提取策略（层层递进）：
    1. Scrapling Fetcher（含 stealth 伪装）→ trafilatura 提取
    2. Playwright 渲染 → trafilatura 提取
    """
    domain = urlparse(url).netloc.replace("www.", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if logger:
        logger.info(f"提取正文: {url}")

    # 第1层：Scrapling 下载（自带 stealthy_headers、浏览器指纹伪装）
    html = _download(url)
    if html:
        body = trafilatura.extract(
            html,
            output_format="markdown",
            include_links=True,
            include_images=True,
            include_tables=True,
            favor_precision=True,
        )
        if body and len(body) > 80:
            if logger:
                logger.info(f"  Scrapling 提取成功: {len(body)} 字符")
            return _make_material(body, url, domain, now)
        elif logger:
            logger.info(f"  Scrapling 拿到 HTML 但未提取到正文 ({len(html)} bytes)")

    # 第2层：Playwright 浏览器渲染（处理 JS 动态页面、反爬页面）
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()

        body = trafilatura.extract(
                html,
                output_format="markdown",
                include_links=True,
                include_images=True,
                include_tables=True,
                favor_precision=True,
            )
        if body and len(body) > 80:
            if logger:
                logger.info(f"  Playwright 渲染提取: {len(body)} 字符")
            return _make_material(body, url, domain, now)
    except Exception as e:
        if logger:
            logger.warning(f"  Playwright 提取失败: {e}")

    return ""


def _make_material(body: str, url: str, source: str, timestamp: str) -> str:
    """包装为素材文档"""
    lines = body.strip().split("\n")
    title = lines[0].replace("# ", "").strip() if lines[0].startswith("#") else "正文素材"

    parts = [
        f"# {title}",
        "",
        f"**来源：** {source}",
        f"**原文链接：** {url}",
        f"**抓取时间：** {timestamp}",
        "",
        "---",
        "",
        body.strip(),
        "",
        "---",
        f"*🤖 HotRadar 内容抓取 · {timestamp}*",
    ]
    return "\n".join(parts)


class ContentFetcher(BaseSpider):
    """选题正文内容抓取器"""

    name = "内容抓取"
    platform = "content"

    def fetch(self, title: str = "", url: str = "", hot_item: HotItem = None) -> str:
        """抓取正文内容

        参数（三选一）：
            url:      文章 URL
            hot_item: Phase 1 的 HotItem
            title:    标题（仅记录）

        返回：
            Markdown 素材字符串
        """
        target_url = url or (hot_item.url if hot_item else "")
        if not target_url:
            self.logger.warning("无 URL，无法抓取")
            return ""

        self.logger.info(f"抓取: {title or target_url}")
        return extract_from_url(target_url, self.logger)
