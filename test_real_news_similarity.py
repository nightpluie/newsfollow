#!/usr/bin/env python3
"""
使用真實新聞標題測試相似度演算法
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from improved_similarity import improved_title_similarity
from main import RequestsCrawler, extract_signals, now_iso
import yaml
from collections import defaultdict

def crawl_and_compare():
    """爬取真實新聞並測試比對"""

    # 載入配置
    with open('./config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    crawler = RequestsCrawler()

    # 爬取所有來源
    all_news = []

    for source_config in config['sources']:
        for section in source_config['sections'][:1]:  # 只爬每個來源的第一個 section
            try:
                html = crawler.fetch_html(section['url'])
                signals = extract_signals(
                    html=html,
                    base_url=section['url'],
                    source_id=source_config['source_id'],
                    source_name=source_config['source_name'],
                    section_id=section['section_id'],
                    domain_contains=source_config.get('domain_contains', ''),
                    selectors=section.get('selectors', []),
                    weight=section.get('weight', 1),
                    crawled_at=now_iso(),
                    max_items=10,  # 只取前 10 則
                )

                for sig in signals:
                    all_news.append({
                        'source': sig.source_name,
                        'title': sig.title,
                        'url': sig.url,
                    })

            except Exception as e:
                print(f"Error crawling {source_config['source_id']}: {e}")

    print(f"\n爬取到 {len(all_news)} 則新聞")

    # 測試相似度
    print("\n" + "="*80)
    print("測試相似度閾值")
    print("="*80)

    # 測試不同閾值的效果
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]

    for threshold in thresholds:
        clusters = cluster_news(all_news, threshold)
        print(f"\n閾值 {threshold}: {len(clusters)} 個群集")

        # 顯示有多個來源的群集
        multi_source_clusters = [c for c in clusters if len(c) > 1]
        print(f"  多來源群集: {len(multi_source_clusters)} 個")

        if multi_source_clusters:
            print("\n  範例群集:")
            for i, cluster in enumerate(multi_source_clusters[:3], 1):
                print(f"\n  群集 {i}:")
                for item in cluster:
                    print(f"    - [{item['source']}] {item['title'][:50]}")


def cluster_news(news_list, threshold):
    """使用相似度閾值進行群集"""
    clusters = []
    used = set()

    for i, news1 in enumerate(news_list):
        if i in used:
            continue

        cluster = [news1]
        used.add(i)

        for j, news2 in enumerate(news_list):
            if j <= i or j in used:
                continue

            sim = improved_title_similarity(news1['title'], news2['title'])

            if sim >= threshold:
                cluster.append(news2)
                used.add(j)

        clusters.append(cluster)

    return clusters


# 手動測試案例（來自真實新聞）
def test_manual_cases():
    """測試手動準備的案例"""

    print("\n" + "="*80)
    print("手動測試案例")
    print("="*80)

    # 應該被識別為同一新聞的案例
    same_news_pairs = [
        # 黃國昌 vs 蘇巧慧政見爭議
        ("黃國昌政見遭打臉！蘇巧慧這麼說", "蘇巧慧回應黃國昌政見爭議"),

        # 日本大選
        ("日眾院大選登場！高市有望勝出拿逾300席", "日本眾議院選舉開跑 高市領先有望拿下300席"),
        ("日本大選決戰日　高市能否大勝定調執政走向", "日本大選決戰　高市衝刺選情"),

        # 火災新聞
        ("一家7口鐵棺火…焦屍身份曝！母斷腸指路", "火災釀7死慘劇 母親悲痛認屍"),

        # NONO 性侵案
        ("NONO捲性侵案2年失業！愛妻朱海君近況曝", "NONO性侵案失業2年 妻子朱海君現況"),

        # 勞保勞退
        ("勞保＋勞退可月領6萬？40歲開始做對「這2件事」就夠了", "勞保勞退月領6萬 40歲要做這2件事"),

        # 林宅血案
        ("「世紀血案」倖存者林奐均走出陰影 22年前曾「勇奪金曲獎」", "林宅血案倖存者林奐均奪金曲 22年前往事"),

        # 豆腐媽媽替身
        ("獨／豆腐媽媽替身命危　楊銘威揭劇組黑幕", "豆腐媽媽替身危急 楊銘威爆料劇組問題"),
    ]

    print("\n應該被識別為【同一新聞】:")
    total_same = len(same_news_pairs)
    correct_same = 0

    for t1, t2 in same_news_pairs:
        sim = improved_title_similarity(t1, t2)
        is_same = sim >= 0.5  # 設定閾值 0.5（降低以提高召回率）
        if is_same:
            correct_same += 1

        status = "✅" if is_same else "❌"
        print(f"\n{status} 相似度: {sim:.3f}")
        print(f"  1. {t1}")
        print(f"  2. {t2}")

    # 應該被識別為不同新聞的案例
    different_news_pairs = [
        ("台積電股價創新高", "NONO捲性侵案2年失業"),
        ("黃國昌政見遭打臉", "回宿舍見「6張毛臉貼窗凝視」女大生嚇呆"),
        ("日本大選登場", "台南過年「住2晚4.5萬」　業者：合理漲價"),
        ("勞保＋勞退可月領6萬", "獨／豆腐媽媽替身命危　楊銘威揭劇組黑幕"),
    ]

    print("\n" + "="*80)
    print("應該被識別為【不同新聞】:")
    total_diff = len(different_news_pairs)
    correct_diff = 0

    for t1, t2 in different_news_pairs:
        sim = improved_title_similarity(t1, t2)
        is_different = sim < 0.5
        if is_different:
            correct_diff += 1

        status = "✅" if is_different else "❌"
        print(f"\n{status} 相似度: {sim:.3f}")
        print(f"  1. {t1}")
        print(f"  2. {t2}")

    # 計算準確率
    print("\n" + "="*80)
    print("驗收結果")
    print("="*80)
    print(f"同一新聞識別率: {correct_same}/{total_same} = {correct_same/total_same*100:.1f}%")
    print(f"不同新聞識別率: {correct_diff}/{total_diff} = {correct_diff/total_diff*100:.1f}%")
    print(f"整體準確率: {(correct_same+correct_diff)/(total_same+total_diff)*100:.1f}%")

    # 驗收標準
    same_rate = correct_same / total_same
    diff_rate = correct_diff / total_diff

    print("\n驗收標準檢查:")
    print(f"  同一新聞識別率 >= 80%: {'✅ PASS' if same_rate >= 0.8 else '❌ FAIL'} ({same_rate*100:.1f}%)")
    print(f"  不同新聞識別率 >= 90%: {'✅ PASS' if diff_rate >= 0.9 else '❌ FAIL'} ({diff_rate*100:.1f}%)")


if __name__ == "__main__":
    # 先測試手動案例
    test_manual_cases()

    # 再測試真實爬取的新聞
    print("\n\n" + "="*80)
    print("測試真實爬取的新聞")
    print("="*80)
    crawl_and_compare()
