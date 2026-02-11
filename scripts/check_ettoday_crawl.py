#!/usr/bin/env python3
"""檢查 ETtoday 是否爬到特定新聞"""

import sys
sys.path.insert(0, '.')

from main import RequestsCrawler, extract_signals, normalize_title
from bs4 import BeautifulSoup

# 目標關鍵字
target_keywords = ["賴清德", "何欣純", "台中"]

print("=" * 60)
print("🔍 檢查 ETtoday 爬取結果")
print("=" * 60)

crawler = RequestsCrawler()

urls = [
    "https://www.ettoday.net/news/news-list.htm",
    "https://www.ettoday.net/news/focus/焦點新聞/",
    "https://www.ettoday.net/news/hot-news.htm",
]

all_found = []

for url in urls:
    print(f"\n📰 爬取: {url}")
    try:
        html = crawler.fetch_html(url)
        soup = BeautifulSoup(html, 'html.parser')

        selectors = [
            "h3 a",
            ".part_list_2 h3 a",
            ".piece h3 a",
        ]

        found_count = 0
        for selector in selectors:
            for link in soup.select(selector):
                title = link.get_text(strip=True)

                # 檢查是否包含目標關鍵字
                if all(keyword in title for keyword in target_keywords):
                    found_count += 1
                    print(f"   ✅ 找到: {title}")
                    all_found.append(title)

        if found_count == 0:
            print(f"   ❌ 未找到包含所有關鍵字的新聞")

    except Exception as e:
        print(f"   ⚠️  錯誤: {e}")

print("\n" + "=" * 60)
print("📊 總結:")
print(f"找到 {len(all_found)} 則相關新聞")
if all_found:
    for i, title in enumerate(all_found, 1):
        print(f"{i}. {title}")
else:
    print("❌ 沒有找到包含【賴清德 + 何欣純 + 台中】的新聞")
print("=" * 60)
