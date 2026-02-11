#!/usr/bin/env python3
"""
找出三立新聞網首頁更好的 selectors
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import RequestsCrawler
from bs4 import BeautifulSoup

def find_setn_news_links():
    """找出三立新聞網首頁的新聞連結"""
    crawler = RequestsCrawler()

    url = "https://www.setn.com/"
    html = crawler.fetch_html(url)
    soup = BeautifulSoup(html, 'html.parser')

    print("="*60)
    print("檢查三立新聞網首頁所有 a 標籤")
    print("="*60)

    # 找出所有包含 News.aspx 或 news/ 的連結
    all_links = soup.find_all('a', href=True)

    news_links = []
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)

        # 篩選新聞連結 (包含 News.aspx 或 star.setn.com/news/)
        if ('News.aspx?NewsID=' in href or
            'star.setn.com/news/' in href or
            'www.setn.com/News.aspx?NewsID=' in href):

            # 過濾掉太短的標題
            if len(text) >= 8:
                news_links.append({
                    'text': text,
                    'href': href,
                    'class': link.get('class', [])
                })

    print(f"\n找到 {len(news_links)} 個新聞連結")
    print("\n前 20 個新聞:")

    for i, link in enumerate(news_links[:20], 1):
        print(f"\n{i}. {link['text'][:60]}")
        print(f"   href: {link['href'][:80]}")
        print(f"   class: {link['class']}")

    # 分析這些連結的共同特徵
    print("\n" + "="*60)
    print("分析 class 分布")
    print("="*60)

    class_count = {}
    for link in news_links:
        classes = ' '.join(link['class']) if link['class'] else 'no-class'
        class_count[classes] = class_count.get(classes, 0) + 1

    for cls, count in sorted(class_count.items(), key=lambda x: x[1], reverse=True):
        print(f"{cls}: {count} 個")

if __name__ == "__main__":
    find_setn_news_links()
