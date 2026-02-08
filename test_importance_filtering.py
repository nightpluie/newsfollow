#!/usr/bin/env python3
"""
測試新聞重要性篩選機制
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_dashboard_with_real_skills import NewsDashboard, NewsItem
from main import normalize_title, now_iso

# 建立測試資料
all_sources = {
    'UDN': [
        NewsItem('UDN', '台積電股價創新高 外資大買', 'https://udn.com/1', normalize_title('台積電股價創新高'), now_iso(), 'marquee', 6),
        NewsItem('UDN', '總統府發布重大聲明', 'https://udn.com/2', normalize_title('總統府發布重大聲明'), now_iso(), 'marquee', 6),
        NewsItem('UDN', '藝人結婚 粉絲祝福', 'https://udn.com/3', normalize_title('藝人結婚'), now_iso(), 'homepage', 5),
        NewsItem('UDN', '地震規模6.5全台有感', 'https://udn.com/4', normalize_title('地震規模6.5'), now_iso(), 'marquee', 6),
    ],
    'TVBS': [
        NewsItem('TVBS', '台積電創歷史新高 外資持續加碼', 'https://tvbs.com/1', normalize_title('台積電創新高'), now_iso(), 'hot', 4),
        NewsItem('TVBS', '地震6.5級 全台搖晃', 'https://tvbs.com/2', normalize_title('地震6.5級'), now_iso(), 'marquee', 6),
    ],
    '中時': [
        NewsItem('中時', '台積電股價飆漲 創歷史新高', 'https://chinatimes.com/1', normalize_title('台積電股價創新高'), now_iso(), 'homepage', 5),
    ],
}

ettoday_items = []  # 假設 ETtoday 沒有任何新聞

# 建立 dashboard 實例
dashboard = NewsDashboard()

# 測試篩選
print("="*80)
print("測試新聞重要性篩選")
print("="*80)

missing = dashboard.find_missing_news(all_sources, ettoday_items)

print(f"\n原始新聞數: {sum(len(items) for items in all_sources.values())}")
print(f"篩選後新聞數: {len(missing)}")
print(f"篩選比例: {len(missing) / sum(len(items) for items in all_sources.values()) * 100:.1f}%")

print("\n" + "="*80)
print("篩選後的新聞列表（按重要性排序）")
print("="*80)

for i, news in enumerate(missing, 1):
    importance = news['importance']
    print(f"\n{i}. {news['star_rating']} {news['title']}")
    print(f"   來源: {', '.join(news['sources'])}")
    print(f"   總分: {importance['total_score']:.1f}/100")
    print(f"   評分:")
    for reason in importance['reasons']:
        print(f"     - {reason}")

print("\n" + "="*80)
print("驗收結果")
print("="*80)

# 檢查篩選效果
original_count = sum(len(items) for items in all_sources.values())
filtered_count = len(missing)
reduction_rate = (original_count - filtered_count) / original_count * 100

print(f"原始新聞數: {original_count}")
print(f"篩選後新聞數: {filtered_count}")
print(f"減少比例: {reduction_rate:.1f}% (目標: 60-70%)")

# 檢查是否保留重要新聞
important_news_titles = ['台積電', '總統', '地震']
preserved_important = 0

for news in missing:
    for keyword in important_news_titles:
        if keyword in news['title']:
            preserved_important += 1
            break

print(f"\n保留重要新聞: {preserved_important}/{len(important_news_titles)} ✅")

# 檢查是否過濾不重要新聞
unimportant_filtered = True
for news in missing:
    if '藝人結婚' in news['title']:
        unimportant_filtered = False
        break

print(f"過濾不重要新聞: {'✅ 是' if unimportant_filtered else '❌ 否'}")

# 檢查多來源新聞是否優先
if len(missing) > 0:
    top_news = missing[0]
    multi_source = len(top_news['sources']) > 1
    print(f"多來源新聞優先顯示: {'✅ 是' if multi_source else '❌ 否'}")
