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
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
import trafilatura
from playwright.sync_api import sync_playwright

from .base import BaseSpider, HotItem


def _download(url: str, timeout: int = 15) -> str:
    """下载 URL 内容（自动处理编码）"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.encoding = resp.apparent_encoding or "utf-8"
    if resp.status_code == 200:
        return resp.text
    return ""


def extract_from_url(url: str, logger=None) -> str:
    """从 URL 提取正文，返回 Markdown 格式素材文档"""
    domain = urlparse(url).netloc.replace("www.", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if logger:
        logger.info(f"提取正文: {url}")

    # 1) requests 下载 + trafilatura 提取
    html = _download(url)
    if html:
        body = trafilatura.extract(
            html,
            output_format="markdown",
            include_links=True,
            include_images=False,
            include_tables=True,
            favor_precision=True,
        )
        if body and len(body) > 50:
            if logger:
                logger.info(f"  提取成功: {len(body)} 字符")
            return _make_material(body, url, domain, now)

    # 2) Playwright 渲染（处理 JS 动态页面）
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()

        body = trafilatura.extract(html, output_format="markdown")
        if body and len(body) > 50:
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
