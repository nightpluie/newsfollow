#!/usr/bin/env python3
"""
測試分組顯示功能
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_dashboard_with_real_skills import NewsDashboard, NewsItem
from main import normalize_title, now_iso

# 建立測試資料 - 模擬同一新聞的不同報導
all_sources = {
    'UDN': [
        NewsItem('UDN', 'LISA確定主演Netflix電影 進軍好萊塢', 'https://udn.com/lisa1',
                normalize_title('LISA Netflix電影'), now_iso(), 'marquee', 6),
        NewsItem('UDN', '台積電股價創新高 外資大買', 'https://udn.com/tsmc1',
                normalize_title('台積電創新高'), now_iso(), 'homepage', 5),
    ],
    'TVBS': [
        NewsItem('TVBS', 'BLACKPINK成員LISA進軍影視圈 Netflix簽約', 'https://tvbs.com/lisa1',
                normalize_title('LISA Netflix'), now_iso(), 'hot', 4),
        NewsItem('TVBS', '台積電飆漲 創歷史新高紀錄', 'https://tvbs.com/tsmc1',
                normalize_title('台積電新高'), now_iso(), 'homepage', 5),
    ],
    '三立': [
        NewsItem('三立', 'LISA演藝事業再擴張 Netflix力邀主演新片', 'https://setn.com/lisa1',
                normalize_title('LISA Netflix新片'), now_iso(), 'homepage', 4),
    ],
}

ettoday_items = []

# 建立 dashboard 實例
dashboard = NewsDashboard()

# 測試分組
print("="*80)
print("測試新聞分組顯示")
print("="*80)

missing = dashboard.find_missing_news(all_sources, ettoday_items)

print(f"\n原始新聞數: {sum(len(items) for items in all_sources.values())}")
print(f"分組後新聞數: {len(missing)}")

print("\n" + "="*80)
print("分組顯示結果")
print("="*80)

for i, news in enumerate(missing, 1):
    print(f"\n【群組 {i}】{news['star_rating']} {news['title']}")
    print(f"  來源數量: {len(news['sources'])} 家媒體")
    print(f"  重要性分數: {news['importance']['total_score']:.1f}/100")

    print(f"\n  各來源報導:")
    for detail in news['source_details']:
        print(f"    - [{detail['source']}] {detail['title']}")
        print(f"      {detail['url']}")

    print(f"\n  [AI 改寫按鈕]")

print("\n" + "="*80)
print("驗收結果")
print("="*80)

# 檢查 LISA 新聞是否被分組
lisa_news = [n for n in missing if 'LISA' in n['title'] or 'lisa' in n['title'].lower()]
if lisa_news:
    lisa = lisa_news[0]
    print(f"✅ LISA 新聞已分組")
    print(f"   來源數: {len(lisa['sources'])} (預期: 3)")
    print(f"   來源: {', '.join(lisa['sources'])}")
    print(f"   各來源標題:")
    for detail in lisa['source_details']:
        print(f"     - {detail['source']}: {detail['title'][:50]}...")

    if len(lisa['sources']) == 3:
        print(f"\n✅ PASS - LISA 新聞成功合併 3 個來源")
    else:
        print(f"\n❌ FAIL - LISA 新聞來源數不正確")
else:
    print("❌ FAIL - 找不到 LISA 新聞")

# 檢查台積電新聞是否被分組
tsmc_news = [n for n in missing if '台積電' in n['title']]
if tsmc_news:
    tsmc = tsmc_news[0]
    print(f"\n✅ 台積電新聞已分組")
    print(f"   來源數: {len(tsmc['sources'])} (預期: 2)")
    print(f"   來源: {', '.join(tsmc['sources'])}")

    if len(tsmc['sources']) == 2:
        print(f"\n✅ PASS - 台積電新聞成功合併 2 個來源")
    else:
        print(f"\n❌ FAIL - 台積電新聞來源數不正確")

# 輸出 JSON 格式（供前端使用）
print("\n" + "="*80)
print("API 回應格式範例")
print("="*80)
if lisa_news:
    print(json.dumps(lisa_news[0], ensure_ascii=False, indent=2))
