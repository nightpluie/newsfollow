#!/usr/bin/env python3
"""
測試 main.py 的改進相似度演算法
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import title_similarity, Signal, detect_events, now_iso

# 測試相似度函數
print("="*80)
print("測試 title_similarity 函數")
print("="*80)

test_pairs = [
    ("黃國昌政見遭打臉！蘇巧慧這麼說", "蘇巧慧回應黃國昌政見爭議", True),
    ("NONO捲性侵案2年失業！愛妻朱海君近況曝", "NONO性侵案失業2年 妻子朱海君現況", True),
    ("台積電股價創新高", "NONO捲性侵案2年失業", False),
]

for t1, t2, should_be_similar in test_pairs:
    sim = title_similarity(t1, t2)
    is_similar = sim >= 0.5
    status = "✅" if is_similar == should_be_similar else "❌"

    print(f"\n{status} 相似度: {sim:.3f} (預期: {'相似' if should_be_similar else '不同'})")
    print(f"  1. {t1[:50]}")
    print(f"  2. {t2[:50]}")

# 測試事件偵測
print("\n" + "="*80)
print("測試 detect_events 函數")
print("="*80)

# 模擬來自不同來源的相同新聞
signals = [
    Signal("udn", "UDN", "homepage", "黃國昌政見遭打臉！蘇巧慧這麼說", "https://udn.com/1", 5, now_iso()),
    Signal("tvbs", "TVBS", "homepage", "蘇巧慧回應黃國昌政見爭議", "https://tvbs.com/1", 5, now_iso()),
    Signal("chinatimes", "中時", "homepage", "黃國昌vs蘇巧慧政見論戰", "https://chinatimes.com/1", 5, now_iso()),

    Signal("udn", "UDN", "homepage", "NONO性侵案失業2年", "https://udn.com/2", 5, now_iso()),
    Signal("setn", "三立", "homepage", "NONO捲性侵案2年失業！愛妻朱海君近況曝", "https://setn.com/2", 5, now_iso()),

    Signal("udn", "UDN", "homepage", "台積電股價創新高", "https://udn.com/3", 5, now_iso()),
]

events = detect_events(
    signals=signals,
    score_threshold=4,
    similarity_threshold=0.5,
)

print(f"\n偵測到 {len(events)} 個事件")

for i, event in enumerate(events, 1):
    print(f"\n事件 {i}:")
    print(f"  標題: {event.canonical_title}")
    print(f"  分數: {event.score}")
    print(f"  來源數: {event.source_count}")
    print(f"  訊號數: {event.signal_count}")
    print(f"  訊號:")
    for sig in event.signals:
        print(f"    - [{sig.source_name}] {sig.title}")

# 驗收
print("\n" + "="*80)
print("驗收結果")
print("="*80)

# 預期應該有 3 個事件（黃國昌, NONO, 台積電）
# 其中黃國昌應該有3個訊號，NONO應該有2個訊號，台積電應該有1個訊號
expected_events = 3
actual_events = len(events)

print(f"事件數量: {actual_events} (預期: {expected_events})")

if actual_events == expected_events:
    print("✅ PASS - 事件數量正確")

    # 檢查群集是否正確
    multi_signal_events = [e for e in events if e.signal_count > 1]
    print(f"多訊號事件數: {len(multi_signal_events)} (預期: 2)")

    if len(multi_signal_events) == 2:
        print("✅ PASS - 成功識別同一新聞的不同報導")
    else:
        print("❌ FAIL - 群集不正確")
else:
    print(f"❌ FAIL - 事件數量不正確 (實際: {actual_events}, 預期: {expected_events})")
