#!/usr/bin/env python3
"""
爬蟲健康度檢查腳本
驗證 UDN 和 TVBS 的選擇器是否仍然有效
"""

import sys
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


def check_selector_health(url: str, selectors: List[str], min_items: int = 5) -> Dict:
    """檢查選擇器健康度"""
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0 Safari/537.36"
                )
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:
        return {
            "status": "failed",
            "error": f"無法訪問 {url}: {exc}",
            "url": url,
        }

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for selector in selectors:
        items = soup.select(selector)
        count = len(items)
        health = "🟢 健康" if count >= min_items else "🔴 失效" if count == 0 else "🟡 警告"

        results.append(
            {
                "selector": selector,
                "count": count,
                "health": health,
                "samples": [item.get_text(strip=True)[:50] for item in items[:3]],
            }
        )

    total_items = sum(r["count"] for r in results)
    overall_health = "🟢 健康" if total_items >= min_items else "🔴 失效"

    return {
        "status": "ok",
        "url": url,
        "overall_health": overall_health,
        "total_items": total_items,
        "selectors": results,
    }


def main() -> int:
    print("=" * 80)
    print("新聞爬蟲健康度檢查")
    print("=" * 80)

    checks = [
        {
            "name": "UDN 首頁",
            "url": "https://udn.com/news/index",
            "selectors": [
                "a.story-list__title-link",
                ".story-list a",
                "main a[href*='/news/story/']",
            ],
        },
        {
            "name": "UDN 熱門",
            "url": "https://udn.com/rank/pv",
            "selectors": [
                ".ranking-list a",
                "table a[href*='/news/story/']",
                "main a[href*='/news/story/']",
            ],
        },
        {
            "name": "TVBS 首頁",
            "url": "https://news.tvbs.com.tw/",
            "selectors": [
                "a.news__title",
                "a[href*='news.tvbs.com.tw/'][title]",
                "main a[href*='news.tvbs.com.tw/']",
            ],
        },
        {
            "name": "TVBS 熱門",
            "url": "https://news.tvbs.com.tw/hot",
            "selectors": [
                ".hot a",
                ".popular a",
                "main a[href*='news.tvbs.com.tw/']",
            ],
        },
    ]

    all_healthy = True

    for check in checks:
        print(f"\n檢查: {check['name']}")
        print(f"URL: {check['url']}")
        print("-" * 80)

        result = check_selector_health(check["url"], check["selectors"])

        if result["status"] == "failed":
            print(f"❌ {result['error']}")
            all_healthy = False
            continue

        print(f"{result['overall_health']} 總計: {result['total_items']} 個項目\n")

        for sel_result in result["selectors"]:
            print(f"  {sel_result['health']} [{sel_result['count']:2d}] {sel_result['selector']}")
            if sel_result["samples"]:
                for sample in sel_result["samples"]:
                    print(f"       ↳ {sample}")

        if "🔴" in result["overall_health"]:
            all_healthy = False

    print("\n" + "=" * 80)
    if all_healthy:
        print("✅ 所有爬蟲健康,可以運作")
        return 0
    else:
        print("⚠️ 部分爬蟲失效,需要更新選擇器")
        return 1


if __name__ == "__main__":
    sys.exit(main())
