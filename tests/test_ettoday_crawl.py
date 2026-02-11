#!/usr/bin/env python3
"""測試 ETtoday 爬取功能"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import RequestsCrawler
from bs4 import BeautifulSoup


def test_ettoday_crawl():
    """測試 ETtoday 爬取"""
    print("=" * 60)
    print("🧪 測試 ETtoday 新聞爬取")
    print("=" * 60)

    crawler = RequestsCrawler()

    test_urls = [
        "https://www.ettoday.net/news/news-list.htm",
        "https://www.ettoday.net/news/focus/focus-list.htm",
    ]

    total_count = 0

    for url in test_urls:
        print(f"\n📍 測試: {url}")
        try:
            html = crawler.fetch_html(url, timeout=15)
            soup = BeautifulSoup(html, 'html.parser')

            selectors = [
                "h3 a",
                ".part_list_2 h3 a",
                ".piece h3 a",
            ]

            count = 0
            for selector in selectors:
                links = soup.select(selector)
                count += len(links)

            print(f"✅ 成功抓取: {count} 個連結")
            total_count += count

            # 顯示前 5 則新聞標題
            print("\n📰 前 5 則新聞:")
            shown = 0
            for selector in selectors:
                for link in soup.select(selector):
                    title = link.get_text(strip=True)
                    if title and len(title) >= 8 and shown < 5:
                        print(f"   {shown + 1}. {title}")
                        shown += 1
                    if shown >= 5:
                        break
                if shown >= 5:
                    break

        except Exception as e:
            print(f"❌ 爬取失敗: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"🎉 測試完成: 總共抓取 {total_count} 個連結")
    print("=" * 60)

    if total_count >= 20:
        print("✅ 測試通過: 成功抓取至少 20 則新聞")
        return True
    else:
        print(f"❌ 測試失敗: 僅抓取 {total_count} 則新聞 (需至少 20 則)")
        return False


if __name__ == "__main__":
    success = test_ettoday_crawl()
    sys.exit(0 if success else 1)
