#!/usr/bin/env python3
"""最終測試：驗證 ETtoday 爬取功能"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_dashboard_with_real_skills import NewsDashboard


def main():
    print("=" * 60)
    print("🧪 最終測試：ETtoday 爬取功能")
    print("=" * 60)

    try:
        dashboard = NewsDashboard()

        print("\n📍 開始爬取 ETtoday 新聞...")
        ettoday_items = dashboard.crawl_ettoday()

        print(f"\n✅ 成功爬取 {len(ettoday_items)} 則 ETtoday 新聞")

        if len(ettoday_items) >= 20:
            print("\n📰 前 10 則新聞標題:")
            for i, item in enumerate(ettoday_items[:10], 1):
                print(f"   {i}. {item.title}")
                print(f"      URL: {item.url}")

            print("\n" + "=" * 60)
            print("✅ 測試通過！ETtoday 爬取功能正常運作")
            print("=" * 60)
            return True
        else:
            print(f"\n❌ 測試失敗：僅抓取 {len(ettoday_items)} 則新聞 (需至少 20 則)")
            return False

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
