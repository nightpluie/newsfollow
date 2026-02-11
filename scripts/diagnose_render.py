#!/usr/bin/env python3
"""
診斷 Render 環境問題
模擬低記憶體和網路延遲環境
"""

import os
import psutil
import time
import traceback
from news_dashboard import NewsDashboard

def get_memory_usage():
    """取得當前記憶體使用量（MB）"""
    process = psutil.Process()
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # 轉換為 MB

def diagnose():
    print("=" * 60)
    print("🔍 Render 環境診斷工具")
    print("=" * 60)

    # 1. 檢查環境變數
    print("\n1️⃣  檢查環境變數...")
    required_vars = ["OPENAI_API_KEY", "OPENAI_MODEL"]
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 隱藏 API Key 的大部分內容
            if "KEY" in var:
                display_value = f"{value[:10]}...{value[-4:]}"
            else:
                display_value = value
            print(f"   ✅ {var} = {display_value}")
        else:
            print(f"   ❌ {var} = 未設定")

    # 2. 檢查記憶體使用
    print("\n2️⃣  記憶體使用監控...")
    print(f"   初始記憶體: {get_memory_usage():.2f} MB")

    # 3. 測試完整流程
    print("\n3️⃣  測試完整爬取流程...")

    try:
        dashboard = NewsDashboard()
        print(f"   Dashboard 初始化後: {get_memory_usage():.2f} MB")

        # 測試爬取
        print("\n   開始爬取新聞來源...")
        start_time = time.time()

        all_source_items = {}
        sources_to_crawl = ["UDN", "TVBS", "中時新聞網", "三立新聞網"]

        for source_name in sources_to_crawl:
            print(f"\n   📰 爬取 {source_name}...")
            items = dashboard.crawl_source(source_name)
            all_source_items[source_name] = items

            mem_usage = get_memory_usage()
            print(f"      → 抓取 {len(items)} 則新聞")
            print(f"      → 記憶體: {mem_usage:.2f} MB")

            # 警告：接近 512MB 上限
            if mem_usage > 400:
                print(f"      ⚠️  警告：記憶體使用接近 512MB 上限！")

        # 測試 ETtoday 爬取（帶快取）
        print(f"\n   📰 爬取 ETtoday（帶快取）...")
        ettoday_items = dashboard.crawl_ettoday()
        print(f"      → 抓取 {len(ettoday_items)} 則新聞")
        print(f"      → 記憶體: {get_memory_usage():.2f} MB")

        # 測試相似度比對
        print(f"\n   🔍 測試相似度比對...")
        missing_news = dashboard.find_missing_news(all_source_items, ettoday_items)

        elapsed = time.time() - start_time
        mem_final = get_memory_usage()

        print(f"\n   ✅ 完整流程測試成功！")
        print(f"      → 耗時: {elapsed:.2f} 秒")
        print(f"      → 最終記憶體: {mem_final:.2f} MB")
        print(f"      → 找到缺少新聞: {len(missing_news)} 則")

        # 顯示 LLM 統計
        stats = dashboard.similarity_checker.get_statistics()
        print(f"      → LLM 調用次數: {stats['llm_call_count']}")

        # 檢查是否超過 512MB
        if mem_final > 512:
            print(f"\n   ❌ 錯誤：記憶體使用超過 512MB 上限！")
            print(f"      這可能是 Render 免費方案失敗的原因。")
            return False

        # 檢查是否超過 300 秒
        if elapsed > 300:
            print(f"\n   ❌ 錯誤：執行時間超過 300 秒 worker timeout！")
            return False

        return True

    except Exception as e:
        print(f"\n   ❌ 發生錯誤：{type(e).__name__}: {e}")
        print(f"\n   完整錯誤堆疊：")
        traceback.print_exc()
        print(f"\n   最終記憶體: {get_memory_usage():.2f} MB")
        return False

def suggest_fixes():
    """提供修復建議"""
    print("\n" + "=" * 60)
    print("💡 修復建議")
    print("=" * 60)

    mem_usage = get_memory_usage()

    if mem_usage > 400:
        print("\n🔴 記憶體問題：")
        print("   1. 升級 Render 方案（付費方案有更多記憶體）")
        print("   2. 減少 max_items（25 → 15）降低資料量")
        print("   3. 使用串流處理（不要一次載入所有新聞）")
        print("   4. 定期清理記憶體（del 不需要的變數）")

    print("\n🟡 Timeout 問題：")
    print("   1. 已設定 API timeout (10秒) ✅")
    print("   2. 已設定 worker timeout (300秒) ✅")
    print("   3. 考慮使用 async 平行處理（加速 LLM 調用）")

    print("\n🟢 環境變數：")
    print("   確認 Render 環境變數設定：")
    print("   - OPENAI_API_KEY")
    print("   - OPENAI_MODEL=gpt-4.1-nano-2025-04-14")
    print("   - ANTHROPIC_API_KEY")

if __name__ == "__main__":
    print("\n⚠️  注意：此腳本會執行實際的 API 調用和爬取")
    print("   請確認已設定環境變數：OPENAI_API_KEY, OPENAI_MODEL\n")

    input("按 Enter 開始診斷...")

    success = diagnose()

    if not success:
        suggest_fixes()
    else:
        print("\n✅ 診斷完成，所有檢查通過！")
        print("   如果 Render 仍然失敗，請提供完整的 Render 日誌。")
