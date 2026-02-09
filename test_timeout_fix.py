#!/usr/bin/env python3
"""
測試 Timeout 修復是否正常運作
"""

import os
import time
from hybrid_similarity import HybridSimilarityChecker

def test_timeout_configuration():
    """測試 timeout 配置"""
    print("=== 測試 1: Timeout 配置 ===")

    checker = HybridSimilarityChecker(
        enable_llm=True,
        timeout=5,  # 5 秒超時
        max_llm_calls=10
    )

    print(f"✅ Timeout: {checker.timeout}秒")
    print(f"✅ Max LLM Calls: {checker.max_llm_calls}")
    print()

def test_max_calls_limit():
    """測試調用次數上限"""
    print("=== 測試 2: LLM 調用次數上限 ===")

    checker = HybridSimilarityChecker(
        enable_llm=True,
        timeout=10,
        max_llm_calls=5  # 設定很低的上限來測試
    )

    # 準備測試標題（相似度在 0.3-0.6 之間，會觸發 LLM）
    test_pairs = [
        ("台積電股價大漲", "TSMC 股價飆升"),
        ("賴清德訪問台中", "賴總統前往中部"),
        ("颱風即將來襲", "強颱接近台灣"),
        ("地震最新消息", "震度資訊更新"),
        ("油價再度上漲", "汽油價格調漲"),
        ("疫情持續升溫", "確診數增加"),
        ("房價創新高", "不動產價格飆升"),
    ]

    for i, (title1, title2) in enumerate(test_pairs, 1):
        result = checker.is_same_news(title1, title2)
        print(f"{i}. '{title1}' vs '{title2}' → {result}")
        print(f"   LLM 調用次數: {checker.llm_call_count}")

        if checker.llm_call_count >= checker.max_llm_calls:
            print(f"   ⚠️  已達到上限（{checker.max_llm_calls}），後續將使用演算法降級")
            break

    print(f"\n最終統計: {checker.get_statistics()}")
    print()

def test_error_handling():
    """測試錯誤處理"""
    print("=== 測試 3: 錯誤處理 ===")

    # 使用無效的 API Key 測試降級機制
    checker = HybridSimilarityChecker(
        api_key="invalid_key",
        enable_llm=True,
        timeout=2
    )

    # 這應該觸發錯誤，然後降級到演算法
    title1 = "台積電股價創新高"
    title2 = "TSMC 股票飆漲"

    print(f"測試標題: '{title1}' vs '{title2}'")
    try:
        result = checker.is_same_news(title1, title2)
        print(f"✅ 降級機制正常運作，結果: {result}")
    except Exception as e:
        print(f"❌ 錯誤未被正確處理: {e}")

    print()

def test_algorithm_only():
    """測試純演算法模式（不使用 LLM）"""
    print("=== 測試 4: 純演算法模式 ===")

    checker = HybridSimilarityChecker(
        enable_llm=False  # 停用 LLM
    )

    test_pairs = [
        ("台積電股價大漲", "台積電股價飆升", True),   # 高相似度
        ("颱風來襲", "地震發生", False),              # 低相似度
        ("賴清德訪問台中", "賴總統前往台中", True),   # 中等相似度
    ]

    for title1, title2, expected in test_pairs:
        result = checker.is_same_news(title1, title2)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{title1}' vs '{title2}' → {result} (預期: {expected})")

    print(f"\nLLM 調用次數: {checker.llm_call_count}（應為 0）")
    print()

if __name__ == "__main__":
    print("🧪 測試 Timeout 修復與降級機制\n")

    test_timeout_configuration()
    test_algorithm_only()

    # 只有在有 API Key 時才測試 LLM 功能
    if os.getenv("OPENAI_API_KEY"):
        test_max_calls_limit()
        test_error_handling()
    else:
        print("⚠️  跳過 LLM 測試（未設定 OPENAI_API_KEY）\n")

    print("✅ 所有測試完成！")
