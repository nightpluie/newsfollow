#!/usr/bin/env python3
"""
測試混合相似度比對功能
"""

from dotenv import load_dotenv
load_dotenv()

from hybrid_similarity import HybridSimilarityChecker

def test_real_case():
    """測試寇世勳新聞案例（實際誤判案例）"""

    print("\n" + "=" * 80)
    print("🧪 測試真實案例：寇世勳道歉新聞")
    print("=" * 80)

    # 初始化檢查器
    checker = HybridSimilarityChecker(enable_llm=True)

    # ETtoday 的標題
    ettoday_title = "快訊／寇世勳道歉！　重磅喊話《世紀血案》劇組：停止後續製作"

    # 其他媒體的標題
    other_titles = [
        ("TVBS", "寇世勳道歉了 自責對林義雄家屬二次傷害"),
        ("三立新聞網", "寇世勳首度發聲了 公開道歉林義雄家屬"),
    ]

    print(f"\n📰 ETtoday 標題:\n  {ettoday_title}")
    print(f"\n🔍 檢查其他媒體的報導是否為同一事件:\n")

    for source, title in other_titles:
        print(f"  來源: {source}")
        print(f"  標題: {title}")

        # 演算法相似度
        from main import title_similarity
        algo_sim = title_similarity(title, ettoday_title)

        # 混合策略判斷
        is_same = checker.is_same_news(title, ettoday_title)

        print(f"  演算法相似度: {algo_sim:.3f}")
        print(f"  混合策略判斷: {'✅ 同一事件' if is_same else '❌ 不同事件'}")
        print(f"  預期結果: ✅ 同一事件")
        print()

    # 顯示統計
    stats = checker.get_statistics()
    print("=" * 80)
    print(f"📊 統計資訊:")
    print(f"  LLM 已啟用: {stats['llm_enabled']}")
    print(f"  LLM 調用次數: {stats['llm_call_count']}")
    print("=" * 80)


def test_different_news():
    """測試完全不同的新聞（應該判斷為不同）"""

    print("\n" + "=" * 80)
    print("🧪 測試完全不同的新聞")
    print("=" * 80)

    checker = HybridSimilarityChecker(enable_llm=True)

    pairs = [
        ("台積電股價創新高", "NONO捲性侵案2年失業！愛妻朱海君近況曝"),
        ("黃國昌政見遭打臉", "回宿舍見「6張毛臉貼窗凝視」女大生嚇呆"),
    ]

    for title1, title2 in pairs:
        print(f"\n  標題 1: {title1}")
        print(f"  標題 2: {title2}")

        from main import title_similarity
        algo_sim = title_similarity(title1, title2)
        is_same = checker.is_same_news(title1, title2)

        print(f"  演算法相似度: {algo_sim:.3f}")
        print(f"  混合策略判斷: {'✅ 同一事件' if is_same else '❌ 不同事件'}")
        print(f"  預期結果: ❌ 不同事件")

    stats = checker.get_statistics()
    print("\n" + "=" * 80)
    print(f"📊 統計資訊:")
    print(f"  LLM 調用次數: {stats['llm_call_count']}")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🚀 開始測試混合相似度比對功能\n")

    # 測試真實案例
    test_real_case()

    # 測試完全不同的新聞
    test_different_news()

    print("\n✅ 測試完成！\n")
