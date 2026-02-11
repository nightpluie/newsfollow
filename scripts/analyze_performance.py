#!/usr/bin/env python3
"""分析系統效能瓶頸"""

# 計算理論數據量
sources = {
    'UDN': 3 * 30,      # 3 sections × 30 items
    'TVBS': 3 * 30,     # 3 sections × 30 items
    '中時': 2 * 30,      # 2 sections × 30 items
    '三立': 2 * 30,      # 2 sections × 30 items
    'ETtoday': 3 * 30,  # 3 URLs × 30 items
}

print("=" * 60)
print("📊 系統效能分析")
print("=" * 60)

total_items = sum(sources.values())
other_sources = sum([sources['UDN'], sources['TVBS'], sources['中時'], sources['三立']])
ettoday_items = sources['ETtoday']

print(f"\n1️⃣ 爬取數據量:")
print(f"   總爬取項目: {total_items} 則新聞")
for name, count in sources.items():
    print(f"   - {name}: {count} 則")

print(f"\n2️⃣ 相似度比對:")
print(f"   其他來源: {other_sources} 則")
print(f"   ETtoday: {ettoday_items} 則")
print(f"   比對次數: {other_sources} × {ettoday_items} = {other_sources * ettoday_items:,} 次")

print(f"\n3️⃣ 時間估算 (無快取):")

# 爬取時間 (平行執行)
crawl_time_parallel = 8  # 秒 (5個來源平行)
print(f"   爬取階段 (平行): ~{crawl_time_parallel} 秒")

# 相似度比對時間
algo_per_comparison = 0.001  # 演算法比對: 1ms
llm_per_call = 0.5  # LLM 調用: 500ms
llm_trigger_rate = 0.20  # 20% 觸發 LLM

comparisons = other_sources * ettoday_items
algo_time = comparisons * algo_per_comparison
llm_calls = comparisons * llm_trigger_rate
llm_time = llm_calls * llm_per_call

print(f"   演算法比對: {comparisons:,} 次 × 1ms = ~{algo_time:.1f} 秒")
print(f"   LLM 調用: {int(llm_calls)} 次 × 500ms = ~{llm_time:.1f} 秒")

total_time = crawl_time_parallel + algo_time + llm_time
print(f"   \n   ⏱️  總計: ~{total_time:.1f} 秒")

print(f"\n4️⃣ 瓶頸分析:")
stages = [
    ("爬取階段", crawl_time_parallel),
    ("演算法比對", algo_time),
    ("LLM 調用", llm_time),
]
stages_sorted = sorted(stages, key=lambda x: x[1], reverse=True)

for stage, time in stages_sorted:
    percentage = (time / total_time) * 100
    print(f"   {stage}: {time:.1f}秒 ({percentage:.1f}%)")

print(f"\n5️⃣ 優化建議:")
if llm_time > crawl_time_parallel:
    print("   ⚠️  LLM 調用是主要瓶頸")
    print("   💡 建議：實作快取機制")
else:
    print("   ✅ 爬取階段是主要瓶頸")
    print("   💡 建議：已使用平行爬取，無需優化")

print("=" * 60)

# 與舊版本比較
print("\n📈 版本比較:")
print("\n   舊版本 (max_items=20):")
old_items = 20
old_other = (3 + 3 + 2 + 2) * 20  # 200
old_et = 2 * 20  # 40
old_comparisons = old_other * old_et
old_time_seq = 5 * 3 + old_comparisons * 0.001 + old_comparisons * 0.2 * 0.5
print(f"   - 總項目: {old_other + old_et}")
print(f"   - 比對次數: {old_comparisons:,}")
print(f"   - 預估時間: ~{old_time_seq:.1f}秒 (依序爬取)")

print("\n   新版本 (max_items=30, 平行爬取):")
print(f"   - 總項目: {total_items}")
print(f"   - 比對次數: {comparisons:,}")
print(f"   - 預估時間: ~{total_time:.1f}秒 (平行爬取)")

improvement = ((old_time_seq - total_time) / old_time_seq) * 100
if improvement > 0:
    print(f"\n   ✅ 效能提升: {improvement:.1f}%")
else:
    print(f"\n   ⚠️  效能下降: {abs(improvement):.1f}%")
    print(f"   原因: 數據量增加 50% (20→30) + LLM 比對增加")

print("=" * 60)
