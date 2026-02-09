#!/usr/bin/env python3
"""
混合相似度比對策略 - 演算法 + LLM 兩階段判斷
使用最便宜的 LLM（GPT-4o-mini）處理邊緣案例
"""

from __future__ import annotations

import os
from typing import List, Dict, Optional

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()  # 從 .env 檔案載入環境變數
except ImportError:
    print("⚠️  未安裝 python-dotenv，請執行: pip install python-dotenv")

from openai import OpenAI
from main import title_similarity, TitleFeatures


class HybridSimilarityChecker:
    """
    混合相似度檢查器

    策略：
    1. 階段 1：演算法快速過濾
       - 相似度 > 0.6 → 直接判定為相同 ✅
       - 相似度 < 0.3 → 直接判定為不同 ❌
       - 0.3 ≤ 相似度 ≤ 0.6 → 進入階段 2

    2. 階段 2：LLM 精確判斷
       - 使用 GPT-4o-mini（最便宜）
       - 簡單 prompt：判斷是否為同一事件
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-nano-2025-04-14", enable_llm: bool = True, timeout: int = 10):
        """
        初始化混合檢查器

        Args:
            api_key: OpenAI API Key（如未提供則從環境變數讀取）
            model: OpenAI 模型名稱（預設 gpt-4.1-nano-2025-04-14，更快更便宜）
            enable_llm: 是否啟用 LLM（False 則只用演算法）
            timeout: API 請求超時時間（秒），預設 10 秒
        """
        self.enable_llm = enable_llm
        self.client = None
        self.model = model
        self.timeout = timeout
        self.llm_call_count = 0  # 統計 LLM 調用次數

        if enable_llm:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("⚠️  未設定 OPENAI_API_KEY，LLM 比對功能將被停用")
                self.enable_llm = False
            else:
                # 設定 timeout 避免請求卡住
                import httpx
                self.client = OpenAI(
                    api_key=api_key,
                    timeout=httpx.Timeout(self.timeout, connect=5.0)  # 總超時 + 連接超時
                )
                print(f"✅ 混合相似度檢查器已啟用 LLM 功能（{model}，timeout={timeout}s）")

    def is_same_news(self, title1: Union[str, TitleFeatures], title2: Union[str, TitleFeatures]) -> bool:
        """
        別斷兩則新聞是否為同一事件
        支援字串或 TitleFeatures
        """
        # 階段 1：演算法快速過濾
        # title_similarity 已經支援 TitleFeatures，直接傳遞即可
        algo_similarity = title_similarity(title1, title2)

        # 高相似度：直接判定為相同
        if algo_similarity >= 0.6:
            return True

        # 低相似度：直接判定為不同
        if algo_similarity < 0.3:
            return False

        # 中間地帶（0.3-0.6）：使用 LLM 確認
        if self.enable_llm and self.client:
            # LLM 需要原始文字
            t1_text = title1.text if isinstance(title1, TitleFeatures) else title1
            t2_text = title2.text if isinstance(title2, TitleFeatures) else title2
            return self._llm_check_similarity(t1_text, t2_text)
        else:
            # 如果 LLM 未啟用，使用保守策略（0.5 閾值）
            return algo_similarity >= 0.5

    def _llm_check_similarity(self, title1: str, title2: str) -> bool:
        """
        使用 LLM 判斷兩則新聞是否為同一事件
        """
        try:
            self.llm_call_count += 1

            prompt = f"""判斷以下兩則台灣新聞標題是否報導同一事件。

標題 1: {title1}
標題 2: {title2}

判斷標準：
- 如果兩則新聞的核心事件、人物、地點相同，即使報導角度不同，也算同一事件
- 例如：「寇世勳道歉了」和「寇世勳喊話劇組停止製作」都是關於同一個道歉事件

只回答 yes 或 no，不要有其他文字。"""

            response = self.client.chat.completions.create(
                model=self.model,  # 使用配置的模型
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0
            )

            answer = response.choices[0].message.content.strip().lower()
            result = answer == "yes"
            return result

        except Exception as e:
            # 區分超時錯誤和其他錯誤
            import httpx
            if isinstance(e, (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout)):
                print(f"⏱️  LLM 調用超時，回退到演算法判斷")
            else:
                print(f"❌ LLM 調用失敗: {type(e).__name__}: {e}")
            # 失敗時回退到演算法（0.5 閾值）
            return title_similarity(title1, title2) >= 0.5

    def batch_check(self, candidate_title: Union[str, TitleFeatures], reference_titles: List[Union[str, TitleFeatures]]) -> bool:
        """
        批次檢查：判斷候選標題是否與參考標題列表中的任何一則相同
        支援傳入預計算的 TitleFeatures 以提升效能
        """
        for ref_title in reference_titles:
            if self.is_same_news(candidate_title, ref_title):
                return True
        return False

    def get_statistics(self) -> Dict:
        """取得統計資訊"""
        return {
            'llm_enabled': self.enable_llm,
            'llm_call_count': self.llm_call_count,
        }

    def reset_statistics(self):
        """重置統計資訊"""
        self.llm_call_count = 0


# ========== 測試程式碼 ==========

def test_hybrid_checker():
    """測試混合檢查器"""

    print("\n" + "=" * 60)
    print("🧪 測試混合相似度檢查器")
    print("=" * 60)

    # 建立檢查器（需要設定 OPENAI_API_KEY 環境變數）
    checker = HybridSimilarityChecker(enable_llm=True)

    # 測試案例 1: 完全相同
    print("\n測試 1: 完全相同")
    t1 = "台積電股價創新高"
    t2 = "台積電股價創新高"
    result = checker.is_same_news(t1, t2)
    print(f"  {t1} vs {t2}")
    print(f"  結果: {result} (預期: True)")

    # 測試案例 2: 同一事件不同切角（會觸發 LLM）
    print("\n測試 2: 同一事件不同切角（觸發 LLM）")
    test_pairs = [
        ("快訊／寇世勳道歉！　重磅喊話《世紀血案》劇組：停止後續製作",
         "寇世勳道歉了 自責對林義雄家屬二次傷害"),

        ("寇世勳首度發聲了 公開道歉林義雄家屬",
         "快訊／寇世勳道歉！　重磅喊話《世紀血案》劇組：停止後續製作"),

        ("台積電股價創新高 外資狂買",
         "護國神山再攻頂 TSMC 股價飆升"),
    ]

    for t1, t2 in test_pairs:
        # 先顯示演算法相似度
        algo_sim = title_similarity(t1, t2)
        result = checker.is_same_news(t1, t2)
        print(f"  標題 1: {t1[:40]}...")
        print(f"  標題 2: {t2[:40]}...")
        print(f"  演算法相似度: {algo_sim:.3f}")
        print(f"  最終判斷: {result}")
        print()

    # 測試案例 3: 完全不同的新聞
    print("\n測試 3: 完全不同的新聞")
    different_pairs = [
        ("台積電股價創新高",
         "NONO捲性侵案2年失業！愛妻朱海君近況曝"),

        ("黃國昌政見遭打臉",
         "回宿舍見「6張毛臉貼窗凝視」女大生嚇呆"),
    ]

    for t1, t2 in different_pairs:
        algo_sim = title_similarity(t1, t2)
        result = checker.is_same_news(t1, t2)
        print(f"  標題 1: {t1[:40]}...")
        print(f"  標題 2: {t2[:40]}...")
        print(f"  演算法相似度: {algo_sim:.3f}")
        print(f"  最終判斷: {result} (預期: False)")
        print()

    # 顯示統計
    stats = checker.get_statistics()
    print("=" * 60)
    print("📊 統計資訊:")
    print(f"  LLM 已啟用: {stats['llm_enabled']}")
    print(f"  LLM 調用次數: {stats['llm_call_count']}")
    print("=" * 60)


if __name__ == "__main__":
    test_hybrid_checker()
