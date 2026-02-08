#!/usr/bin/env python3
"""
新聞重要性評分機制

評分因素：
1. 來源數量（40%）- 多家媒體都有 = 更重要
2. 權重分數（30%）- 來源的 weight 值總和
3. Section 類型（20%）- marquee > hot > homepage
4. 標題關鍵字（10%）- 包含重要關鍵字
"""

from __future__ import annotations
from typing import List, Dict, Set
import re

# 重要關鍵字（可以擴充）
IMPORTANT_KEYWORDS = {
    # 政治
    '總統', '行政院', '立法院', '內閣', '閣揆', '院長', '部長', '市長', '縣長',
    '選舉', '投票', '罷免', '公投', '修法', '法案',

    # 經濟金融
    '台積電', 'tsmc', '聯發科', '鴻海', '台股', '大盤', '外資', '央行',
    '升息', '降息', '通膨', '經濟', 'gdp', '失業率',

    # 災難事件
    '地震', '颱風', '火災', '爆炸', '車禍', '意外', '死亡', '傷亡',
    '淹水', '土石流', '停電', '斷電',

    # 國際重大
    '美國', '中國', '日本', '俄羅斯', '戰爭', '衝突', '制裁',
    '川普', 'trump', '拜登', 'biden', '習近平', '普丁',

    # 社會重大
    '槍擊', '性侵', '綁架', '詐騙', '貪污', '弊案', '醜聞',
    '示威', '抗議', '罷工',

    # 科技
    'ai', '人工智慧', '晶片', '半導體', 'apple', '蘋果', 'google',

    # 健康
    '疫情', '確診', '病毒', '疫苗', '流感',
}

# Section 權重
SECTION_WEIGHTS = {
    'marquee': 1.0,     # 跑馬燈新聞
    'hot': 0.8,         # 熱門新聞
    'homepage': 0.6,    # 首頁新聞
    'realtime': 0.6,    # 即時新聞
    'viewall': 0.5,     # 全部新聞
}


def calculate_news_importance(
    title: str,
    sources: List[str],
    sections_info: List[Dict],  # [{'source': 'UDN', 'section': 'marquee', 'weight': 6}, ...]
) -> Dict:
    """
    計算新聞重要性分數

    參數:
        title: 新聞標題
        sources: 來源列表（例如：['UDN', 'TVBS', '中時']）
        sections_info: 各來源的詳細資訊

    返回:
        {
            'total_score': 總分（0-100）,
            'source_score': 來源分數,
            'weight_score': 權重分數,
            'section_score': Section 分數,
            'keyword_score': 關鍵字分數,
            'star_rating': 星級（1-5）,
            'reasons': 評分原因列表,
        }
    """

    reasons = []

    # 1. 來源數量分數（40%，滿分40）
    source_count = len(set(sources))
    if source_count >= 4:
        source_score = 40
        reasons.append(f"4+ 家媒體報導 (+40)")
    elif source_count == 3:
        source_score = 35
        reasons.append(f"3 家媒體報導 (+35)")
    elif source_count == 2:
        source_score = 25
        reasons.append(f"2 家媒體報導 (+25)")
    else:
        source_score = 10
        reasons.append(f"單一媒體報導 (+10)")

    # 2. 權重分數（30%，滿分30）
    # 累加所有來源的 weight 值
    total_weight = sum(info.get('weight', 1) for info in sections_info)
    # 正規化：假設最高權重總和為 18（3 sources * weight 6）
    weight_score = min(total_weight / 18 * 30, 30)
    reasons.append(f"權重總和 {total_weight} (+{weight_score:.1f})")

    # 3. Section 類型分數（20%，滿分20）
    section_scores = []
    for info in sections_info:
        section_id = info.get('section', 'homepage')
        section_weight = SECTION_WEIGHTS.get(section_id, 0.5)
        section_scores.append(section_weight)

    if section_scores:
        avg_section_weight = sum(section_scores) / len(section_scores)
        section_score = avg_section_weight * 20
        reasons.append(f"Section 平均權重 {avg_section_weight:.2f} (+{section_score:.1f})")
    else:
        section_score = 10

    # 4. 標題關鍵字分數（10%，滿分10，重要關鍵字額外加分）
    title_lower = title.lower()
    matched_keywords = [kw for kw in IMPORTANT_KEYWORDS if kw in title_lower]

    # 基礎關鍵字分數
    if len(matched_keywords) >= 3:
        keyword_score = 10
        reasons.append(f"包含 {len(matched_keywords)} 個重要關鍵字 (+10)")
    elif len(matched_keywords) == 2:
        keyword_score = 7
        reasons.append(f"包含 2 個重要關鍵字 (+7)")
    elif len(matched_keywords) == 1:
        keyword_score = 4
        reasons.append(f"包含 1 個重要關鍵字 (+4)")
    else:
        keyword_score = 0

    # 特別重要關鍵字額外加分（災難、政治重大事件等）
    super_important_keywords = {'地震', '颱風', '火災', '爆炸', '總統', '行政院', '戰爭', '槍擊'}
    super_matched = [kw for kw in super_important_keywords if kw in title_lower]

    bonus = 0
    if super_matched:
        bonus = 20  # 額外加 20 分
        reasons.append(f"包含重大關鍵字 ({', '.join(super_matched)}) (+{bonus})")

    # 總分（加上額外加分）
    total_score = source_score + weight_score + section_score + keyword_score + bonus

    # 星級評分（1-5 星）
    if total_score >= 80:
        star_rating = 5
    elif total_score >= 65:
        star_rating = 4
    elif total_score >= 50:
        star_rating = 3
    elif total_score >= 35:
        star_rating = 2
    else:
        star_rating = 1

    return {
        'total_score': round(total_score, 1),
        'source_score': source_score,
        'weight_score': round(weight_score, 1),
        'section_score': round(section_score, 1),
        'keyword_score': keyword_score,
        'star_rating': star_rating,
        'reasons': reasons,
        'matched_keywords': matched_keywords,
    }


def should_show_news(importance_result: Dict, source_count: int) -> bool:
    """
    判斷新聞是否應該顯示

    篩選條件：
    - 至少 2 家來源 OR
    - 單一來源但評分 >= 60 分（3 星以上）
    """
    if source_count >= 2:
        return True

    if importance_result['total_score'] >= 60:
        return True

    return False


def format_star_rating(star_rating: int) -> str:
    """格式化星級評分"""
    return "⭐" * star_rating


# ========== 測試程式碼 ==========

def test_importance_scoring():
    """測試重要性評分"""

    print("="*80)
    print("測試新聞重要性評分機制")
    print("="*80)

    test_cases = [
        {
            'title': '台積電股價創新高 外資大買',
            'sources': ['UDN', 'TVBS', '中時'],
            'sections_info': [
                {'source': 'UDN', 'section': 'marquee', 'weight': 6},
                {'source': 'TVBS', 'section': 'hot', 'weight': 4},
                {'source': '中時', 'section': 'homepage', 'weight': 5},
            ],
            'expected': '高分（多來源 + 重要關鍵字）',
        },
        {
            'title': '總統府發布重大聲明 回應中國威脅',
            'sources': ['UDN'],
            'sections_info': [
                {'source': 'UDN', 'section': 'marquee', 'weight': 6},
            ],
            'expected': '高分（單一來源但關鍵字重要）',
        },
        {
            'title': '藝人結婚 粉絲祝福',
            'sources': ['三立'],
            'sections_info': [
                {'source': '三立', 'section': 'homepage', 'weight': 4},
            ],
            'expected': '低分（單一來源且無關鍵字）',
        },
        {
            'title': '地震規模 6.5 全台有感',
            'sources': ['UDN', 'TVBS'],
            'sections_info': [
                {'source': 'UDN', 'section': 'marquee', 'weight': 6},
                {'source': 'TVBS', 'section': 'marquee', 'weight': 6},
            ],
            'expected': '極高分（災難新聞 + 多來源）',
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n測試案例 {i}: {case['title']}")
        print(f"預期: {case['expected']}")

        result = calculate_news_importance(
            title=case['title'],
            sources=case['sources'],
            sections_info=case['sections_info'],
        )

        print(f"\n結果:")
        print(f"  總分: {result['total_score']:.1f}/100")
        print(f"  星級: {format_star_rating(result['star_rating'])} ({result['star_rating']} 星)")
        print(f"  是否顯示: {'✅ 是' if should_show_news(result, len(case['sources'])) else '❌ 否'}")
        print(f"\n  評分細節:")
        for reason in result['reasons']:
            print(f"    - {reason}")

        if result['matched_keywords']:
            print(f"  匹配關鍵字: {', '.join(result['matched_keywords'])}")


if __name__ == "__main__":
    test_importance_scoring()
