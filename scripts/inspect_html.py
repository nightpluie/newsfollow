#!/usr/bin/env python3
"""
檢查網頁結構 - 找出更精準的 CSS selectors
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import RequestsCrawler
from bs4 import BeautifulSoup

def inspect_chinatimes():
    """檢查中時新聞網結構"""
    crawler = RequestsCrawler()

    print("\n" + "="*60)
    print("檢查中時新聞網")
    print("="*60)

    url = "https://www.chinatimes.com/realtimenews/?chdtv"
    html = crawler.fetch_html(url)
    soup = BeautifulSoup(html, 'html.parser')

    # 檢查 h3 a
    h3_links = soup.select('h3 a')
    print(f"\n'h3 a' 找到 {len(h3_links)} 個連結")
    for i, link in enumerate(h3_links[:5], 1):
        print(f"  {i}. {link.get_text(strip=True)[:50]}")
        print(f"     href: {link.get('href', '')}")

    # 檢查 .title a
    title_links = soup.select('.title a')
    print(f"\n'.title a' 找到 {len(title_links)} 個連結")
    for i, link in enumerate(title_links[:5], 1):
        print(f"  {i}. {link.get_text(strip=True)[:50]}")
        print(f"     href: {link.get('href', '')}")

    # 檢查文章列表容器
    articles = soup.select('article')
    print(f"\n'article' 找到 {len(articles)} 個")

    # 檢查可能的列表容器
    print("\n可能的列表容器:")
    for cls in ['.vertical-list', '.article-list', '.news-list', '.list-item']:
        items = soup.select(cls)
        if items:
            print(f"  {cls}: {len(items)} 個")

def inspect_setn():
    """檢查三立新聞網結構"""
    crawler = RequestsCrawler()

    print("\n" + "="*60)
    print("檢查三立新聞網")
    print("="*60)

    # 檢查 ViewAll 頁面
    url1 = "https://www.setn.com/ViewAll.aspx"
    html1 = crawler.fetch_html(url1)
    soup1 = BeautifulSoup(html1, 'html.parser')

    print(f"\n【ViewAll 頁面】")

    # 檢查 h3 a
    h3_links = soup1.select('h3 a')
    print(f"\n'h3 a' 找到 {len(h3_links)} 個連結")
    for i, link in enumerate(h3_links[:5], 1):
        print(f"  {i}. {link.get_text(strip=True)[:50]}")
        print(f"     href: {link.get('href', '')}")

    # 檢查 .newsItems-title a
    newsitems_links = soup1.select('.newsItems-title a')
    print(f"\n'.newsItems-title a' 找到 {len(newsitems_links)} 個連結")

    # 檢查首頁
    url2 = "https://www.setn.com/"
    html2 = crawler.fetch_html(url2)
    soup2 = BeautifulSoup(html2, 'html.parser')

    print(f"\n【首頁】")

    # 檢查 .news-title a
    news_title_links = soup2.select('.news-title a')
    print(f"\n'.news-title a' 找到 {len(news_title_links)} 個連結")
    for i, link in enumerate(news_title_links[:10], 1):
        print(f"  {i}. {link.get_text(strip=True)[:50]}")
        print(f"     href: {link.get('href', '')}")

    # 檢查是否有更好的選擇器
    print("\n可能的更好選擇器:")
    for cls in ['.newsItems', '.newsItems-img-wrapper', 'article', '.news-item']:
        items = soup2.select(cls)
        if items:
            print(f"  {cls}: {len(items)} 個")

if __name__ == "__main__":
    inspect_chinatimes()
    inspect_setn()
