#!/usr/bin/env python3
"""測試實際案例的相似度分數"""

from main import title_similarity
from hybrid_similarity import HybridSimilarityChecker
import os
from dotenv import load_dotenv

load_dotenv()

# 實際案例
title1 = "賴清德五度造訪台中 何欣純：有信心贏回台中"
title2 = "賴清德頻赴台中力挺　何欣純：年底「決戰中台灣」是重中之重"

print("=" * 60)
print("📊 相似度分析")
print("=" * 60)
print(f"標題 1: {title1}")
print(f"標題 2: {title2}")
print("=" * 60)

# 測試演算法相似度
algo_score = title_similarity(title1, title2)
print(f"\n1️⃣ 演算法相似度: {algo_score:.4f}")

if algo_score >= 0.6:
    print("   → 判定: 同一新聞 (≥ 0.6)")
elif algo_score >= 0.5:
    print("   → 判定: 同一新聞 (≥ 0.5，混合策略閾值)")
elif algo_score >= 0.3:
    print("   → 判定: 需要 LLM 確認 (0.3-0.6 灰色地帶)")
else:
    print("   → 判定: 不同新聞 (< 0.3)")

# 測試混合策略
print("\n2️⃣ 混合策略測試:")
checker = HybridSimilarityChecker(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    enable_llm=True
)

is_same = checker.is_same_news(title1, title2)
print(f"   結果: {'✅ 同一新聞' if is_same else '❌ 不同新聞'}")
print(f"   LLM 調用次數: {checker.llm_call_count}")

print("\n" + "=" * 60)
print("📈 建議:")
if algo_score < 0.3 and is_same:
    print("⚠️  演算法相似度過低，但 LLM 判定為同一新聞")
    print("   建議：降低演算法閾值至 0.25，讓更多案例進入 LLM 判斷")
elif algo_score >= 0.3 and algo_score < 0.6 and not is_same:
    print("⚠️  進入灰色地帶，但 LLM 判定為不同新聞")
    print("   建議：檢查 LLM prompt 或提高演算法權重")
elif algo_score >= 0.6:
    print("✅ 演算法相似度足夠，應直接判定為同一新聞")
else:
    print("📊 數據正常，混合策略運作正常")
print("=" * 60)
