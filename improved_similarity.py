#!/usr/bin/env python3
"""
改進的新聞標題相似度演算法

策略：
1. 提取關鍵詞（去除停用詞、標點符號）
2. 使用多種相似度指標：
   - Jaccard 相似度（集合交集）
   - 餘弦相似度（TF-IDF）
   - 最長公共子序列比例
3. 加權組合多個指標
"""

from __future__ import annotations
import re
from typing import List, Set
from collections import Counter
import math
import jieba

# 中文停用詞（常見的無意義詞彙）
CHINESE_STOPWORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一個',
    '上', '也', '很', '到', '說', '要', '去', '你', '會', '著', '沒有', '看', '好',
    '自己', '這', '那', '與', '及', '或', '等', '被', '將', '於', '為', '以',
    '！', '？', '，', '。', '：', '；', '、', '「', '」', '『', '』', '（', '）',
    '【', '】', '《', '》', '〈', '〉', '．', '・', '…', '—', '～', '｜', '/', '|',
}

# 英文停用詞
ENGLISH_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'should', 'can', 'could', 'may', 'might', 'must', 'this',
    'that', 'these', 'those', 'it', 'its',
}

ALL_STOPWORDS = CHINESE_STOPWORDS | ENGLISH_STOPWORDS


def tokenize_chinese(text: str) -> List[str]:
    """
    中文分詞（使用 jieba 工具）
    """
    # 使用 jieba 分詞
    tokens = list(jieba.cut(text.lower()))

    # 過濾掉純空白和標點符號
    tokens = [t.strip() for t in tokens if t.strip() and not re.match(r'^[^\w]+$', t)]

    return tokens


def extract_keywords(title: str) -> Set[str]:
    """提取標題中的關鍵詞（去除停用詞）"""
    tokens = tokenize_chinese(title)

    # 去除停用詞
    keywords = {token for token in tokens if token not in ALL_STOPWORDS and len(token) > 0}

    return keywords


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """計算 Jaccard 相似度（集合交集比例）"""
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


def cosine_similarity(text1: str, text2: str) -> float:
    """計算餘弦相似度（基於詞頻）"""
    tokens1 = tokenize_chinese(text1)
    tokens2 = tokenize_chinese(text2)

    # 去除停用詞
    tokens1 = [t for t in tokens1 if t not in ALL_STOPWORDS]
    tokens2 = [t for t in tokens2 if t not in ALL_STOPWORDS]

    if not tokens1 or not tokens2:
        return 0.0

    # 計算詞頻
    counter1 = Counter(tokens1)
    counter2 = Counter(tokens2)

    # 取得所有詞彙
    all_tokens = set(counter1.keys()) | set(counter2.keys())

    # 計算向量
    vec1 = [counter1.get(token, 0) for token in all_tokens]
    vec2 = [counter2.get(token, 0) for token in all_tokens]

    # 計算餘弦相似度
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(v ** 2 for v in vec1))
    magnitude2 = math.sqrt(sum(v ** 2 for v in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def longest_common_substring_ratio(s1: str, s2: str) -> float:
    """計算最長公共子字串比例"""
    if not s1 or not s2:
        return 0.0

    # 移除空白和標點符號
    s1_clean = re.sub(r'\s+', '', s1)
    s2_clean = re.sub(r'\s+', '', s2)

    m, n = len(s1_clean), len(s2_clean)

    if m == 0 or n == 0:
        return 0.0

    # 動態規劃找最長公共子字串
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    max_len = 0

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1_clean[i - 1] == s2_clean[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                max_len = max(max_len, dp[i][j])

    # 回傳最長公共子字串佔較短字串的比例
    return max_len / min(m, n)


def extract_numbers(text: str) -> Set[str]:
    """提取數字（數字往往是新聞的重要特徵）"""
    # 提取所有數字
    numbers = re.findall(r'\d+', text)
    return set(numbers)


def has_common_entity(title1: str, title2: str, min_length: int = 2) -> bool:
    """檢查兩個標題是否有共同的實體（長度 >= min_length 的連續詞組）"""
    tokens1 = tokenize_chinese(title1)
    tokens2 = tokenize_chinese(title2)

    # 去除停用詞
    tokens1 = [t for t in tokens1 if t not in ALL_STOPWORDS and len(t) >= min_length]
    tokens2 = [t for t in tokens2 if t not in ALL_STOPWORDS and len(t) >= min_length]

    # 檢查是否有共同詞
    common_tokens = set(tokens1) & set(tokens2)

    return len(common_tokens) >= 2  # 至少兩個共同詞


def improved_title_similarity(title1: str, title2: str, threshold_boost: bool = True) -> float:
    """
    改進的標題相似度演算法

    策略：
    1. 如果其中一個標題完全包含另一個，視為高度相似（0.85）
    2. 提取數字特徵（新聞中的數字往往是關鍵資訊）
    3. 計算關鍵詞 Jaccard 相似度
    4. 計算餘弦相似度
    5. 計算最長公共子字串比例
    6. 檢查是否有共同實體（人名、地名等）
    7. 加權組合

    權重：
    - 關鍵詞 Jaccard: 35%
    - 餘弦相似度: 30%
    - 最長公共子字串: 25%
    - 數字匹配: 10%
    """
    if not title1 or not title2:
        return 0.0

    # 正規化（小寫、去除多餘空白）
    t1 = ' '.join(title1.lower().split())
    t2 = ' '.join(title2.lower().split())

    # 完全相同
    if t1 == t2:
        return 1.0

    # 子字串包含
    if t1 in t2 or t2 in t1:
        return 0.85

    # 提取關鍵詞
    keywords1 = extract_keywords(title1)
    keywords2 = extract_keywords(title2)

    # 提取數字
    numbers1 = extract_numbers(title1)
    numbers2 = extract_numbers(title2)

    # 如果關鍵詞太少，降低信心
    if len(keywords1) < 3 or len(keywords2) < 3:
        confidence_penalty = 0.9
    else:
        confidence_penalty = 1.0

    # 計算各種相似度
    jaccard = jaccard_similarity(keywords1, keywords2)
    cosine = cosine_similarity(title1, title2)
    lcs_ratio = longest_common_substring_ratio(title1, title2)

    # 數字匹配度
    if numbers1 and numbers2:
        number_match = jaccard_similarity(numbers1, numbers2)
    else:
        number_match = 0.0

    # 檢查是否有共同實體
    has_entity = has_common_entity(title1, title2, min_length=2)

    # 加權組合
    combined_similarity = (
        jaccard * 0.35 +
        cosine * 0.30 +
        lcs_ratio * 0.25 +
        number_match * 0.10
    ) * confidence_penalty

    # 如果有共同實體，大幅提升相似度
    if threshold_boost and has_entity:
        if 0.15 <= combined_similarity < 0.7:
            # 根據基礎相似度和共同詞數量調整提升幅度
            common_keywords_count = len(keywords1 & keywords2)
            if common_keywords_count >= 3:
                boost = 0.30
            elif common_keywords_count >= 2:
                boost = 0.25
            else:
                boost = 0.20
            combined_similarity = min(combined_similarity + boost, 0.85)

    # 如果數字完全匹配且有共同詞，額外加分（重要數字特徵）
    if numbers1 and numbers2 and number_match >= 0.5:
        if len(keywords1 & keywords2) >= 1:  # 只要有一個共同詞就加分
            combined_similarity = min(combined_similarity + 0.15, 0.9)

    return combined_similarity


# ========== 測試程式碼 ==========

def test_similarity():
    """測試相似度演算法"""

    # 測試案例 1: 完全相同
    print("\n測試 1: 完全相同")
    t1 = "台積電股價創新高"
    t2 = "台積電股價創新高"
    sim = improved_title_similarity(t1, t2)
    print(f"{t1} vs {t2}")
    print(f"相似度: {sim:.3f} (預期: 1.0)")

    # 測試案例 2: 同一新聞不同切角
    print("\n測試 2: 同一新聞不同切角")
    test_pairs = [
        ("台積電股價創新高", "護國神山再攻頂"),
        ("黃國昌政見遭打臉！蘇巧慧這麼說", "蘇巧慧回應黃國昌政見爭議"),
        ("日眾院大選登場！高市有望勝出拿逾300席", "日本眾議院選舉開跑 高市領先"),
        ("一家7口鐵棺火…焦屍身份曝！母斷腸指路", "火災釀7死慘劇 母親悲痛認屍"),
    ]

    for t1, t2 in test_pairs:
        sim = improved_title_similarity(t1, t2)
        print(f"{t1[:30]}... vs {t2[:30]}...")
        print(f"相似度: {sim:.3f}")

    # 測試案例 3: 完全不同的新聞
    print("\n測試 3: 完全不同的新聞")
    different_pairs = [
        ("台積電股價創新高", "NONO捲性侵案2年失業！愛妻朱海君近況曝"),
        ("黃國昌政見遭打臉", "回宿舍見「6張毛臉貼窗凝視」女大生嚇呆"),
    ]

    for t1, t2 in different_pairs:
        sim = improved_title_similarity(t1, t2)
        print(f"{t1[:30]}... vs {t2[:30]}...")
        print(f"相似度: {sim:.3f} (預期: < 0.3)")


if __name__ == "__main__":
    test_similarity()
