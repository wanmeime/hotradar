#!/usr/bin/env python3
"""调试知乎搜索"""
from playwright.sync_api import sync_playwright
from urllib.parse import quote

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    title = "网友揭秘安徽无为板鸭其实是鹅"
    search_url = f"https://www.zhihu.com/search?type=content&q={quote(title)}"
    print(f"Search URL: {search_url}")
    
    page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(5000)
    
    body = page.inner_text("body")
    print(f"\nBody length: {len(body)}")
    print(f"\nFirst 2000 chars:")
    print(body[:2000])
    
    # Check all links
    links = page.query_selector_all("a")
    zhihu_links = [l for l in links if l.get_attribute("href") and ("/question/" in l.get_attribute("href") or "/answer/" in l.get_attribute("href") or "/p/" in l.get_attribute("href"))]
    print(f"\n\nZhihu content links ({len(zhihu_links)}):")
    for link in zhihu_links[:5]:
        href = link.get_attribute("href")
        text = link.inner_text().strip()[:80]
        print(f"  [{text}] -> {href}")
    
    browser.close()
