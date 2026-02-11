#!/usr/bin/env python3
"""
測試腳本：模擬大量新聞標題比對，驗證緩存分詞的效能與記憶體回收
"""
import time
import random
import jieba
import gc
import sys
import os

# 確保能導入 main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import title_similarity, get_jieba_tokens

def generate_fake_titles(count=100):
    """生成假新聞標題"""
    subjects = ["台積電", "輝達", "蘋果", "特斯拉", "馬斯克", "黃仁勳", "庫克", "拜登", "川普"]
    actions = ["宣布", "推出", "裁員", "大漲", "暴跌", "收購", "投資", "訪台", "演講"]
    objects = ["新晶片", "電動車", "AI模型", "股價", "財報", "iPhone 16", "超級電腦"]
    suffixes = ["震撼業界", "分析師看好", "股民嗨翻", "引發關注", "市場解讀", "懶人包", "最新消息"]
    
    titles = []
    for _ in range(count):
        t = f"{random.choice(subjects)}{random.choice(actions)}{random.choice(objects)} {random.choice(suffixes)}"
        titles.append(t)
    return titles

def test_performance():
    print("="*60)
    print("🚀 開始效能測試 (模擬 Render 環境)")
    print("="*60)
    
    # 預熱 jieba
    start = time.time()
    jieba.cut("預熱")
    print(f"📦 Jieba 初始化耗時: {time.time() - start:.4f}s")
    
    # 產生測試資料
    N = 100  # 模擬 5 個來源 x 20 篇 = 100 篇
    M = 100  # 模擬 ETtoday 100 篇
    
    print(f"📊 產生測試資料: 來源新聞 {N} 篇 vs ETtoday {M} 篇")
    source_titles = generate_fake_titles(N)
    ettoday_titles = generate_fake_titles(M)
    
    # 第一次執行 (建立緩存)
    print("\n🔄 第 1 次比對 (建立緩存)...")
    start_time = time.time()
    comparisons = 0
    
    for t1 in source_titles:
        for t2 in ettoday_titles:
            sim = title_similarity(t1, t2)
            comparisons += 1
            
    duration1 = time.time() - start_time
    print(f"✅ 完成 {comparisons} 次比對，耗時: {duration1:.4f}s")
    print(f"   平均每對耗時: {duration1/comparisons*1000:.4f}ms")
    
    # 驗證緩存資訊
    info = get_jieba_tokens.cache_info()
    print(f"💾 緩存狀態: {info}")
    
    # 第二次執行 (使用緩存) - 模擬下一輪分析或重複標題
    print("\n🔄 第 2 次比對 (模擬重複標題/下一輪)...")
    start_time = time.time()
    comparisons = 0
    
    # 故意重複使用相同的標題列表
    for t1 in source_titles:
        for t2 in ettoday_titles:
            sim = title_similarity(t1, t2)
            comparisons += 1
            
    duration2 = time.time() - start_time
    print(f"✅ 完成 {comparisons} 次比對，耗時: {duration2:.4f}s")
    print(f"🚀 效能提升: {(duration1 / duration2):.2f}x")
    
    print("\n🧹 測試 gc.collect()...")
    start_gc = time.time()
    gc.collect()
    print(f"✅ GC 耗時: {time.time() - start_gc:.4f}s")

if __name__ == "__main__":
    test_performance()
