# Newsfollow 設計審查報告

## 專案目標回顧

監控台灣多家媒體網站,自動偵測重大新聞事件,並產生 ETtoday 發布用草稿。

**當前實作:** UDN + TVBS (實驗階段)
**擴展目標:** 支援 10+ 家媒體

---

## 🔴 關鍵設計缺陷

### 1. 程式碼組織問題

**問題:** `main.py` 有 1133 行,違反 800 行上限規範

**影響:**
- 難以維護和測試
- 新增媒體來源時修改風險高
- 違反單一職責原則

**建議重構:**
```
newsfollow/
├── core/
│   ├── models.py          # Signal, Event 等資料模型
│   └── config.py          # 設定載入與驗證
├── crawler/
│   ├── base.py            # 爬蟲基底類別
│   ├── requests_backend.py
│   └── openclaw_backend.py
├── detection/
│   ├── clustering.py      # 事件聚類演算法
│   └── scoring.py         # 評分機制
├── generation/
│   └── draft_generator.py # LLM 草稿生成
├── publisher/
│   └── adapters.py        # 發布介面卡
├── storage/
│   └── repository.py      # 資料庫操作
└── main.py                # 主程式進入點 (<200 行)
```

### 2. 測試覆蓋率為零

**問題:** 完全沒有測試,違反 80% 覆蓋率要求

**風險:**
- 無法確保程式正確性
- 重構時容易引入 bug
- 上線後難以除錯

**必須加入的測試:**
```python
tests/
├── unit/
│   ├── test_clustering.py      # 聚類演算法單元測試
│   ├── test_scoring.py         # 評分邏輯單元測試
│   └── test_title_similarity.py
├── integration/
│   ├── test_crawler.py         # 爬蟲整合測試
│   ├── test_repository.py     # 資料庫整合測試
│   └── test_llm_generation.py # LLM 整合測試
└── e2e/
    └── test_workflow.py        # 端到端測試
```

### 3. CSS 選擇器脆弱性 (最嚴重)

**問題:** 媒體網站改版會導致爬蟲立即失效

**當前實作:**
```yaml
selectors:
  - "a.story-list__title-link"  # 高度依賴 class name
  - ".breaking-news a"
```

**失效場景:**
- UDN/TVBS 網站改版
- CSS class 名稱變更
- HTML 結構調整

**改進方案:**

**方案 A: 多層 Fallback**
```yaml
selectors:
  primary:
    - "a.story-list__title-link"
  secondary:
    - ".story-list a"
    - "article a[href*='/news/']"
  generic:
    - "main a[href]"
```

**方案 B: 健康度監控**
```python
class SelectorHealthCheck:
    def check(self, url, selectors):
        """檢查選擇器是否仍有效"""
        results = fetch_with_selectors(url, selectors)

        if len(results) < 5:
            alert("選擇器可能失效: {url}")
            # 自動嘗試 generic selectors
            fallback_results = fetch_with_generic(url)
            return fallback_results

        return results
```

**方案 C: 自適應選擇器 (進階)**
- 使用 AI 分析頁面結構
- 自動學習新的選擇器模式
- 需要較高開發成本

### 4. 同步爬蟲效能瓶頸

**問題:** 爬蟲是同步執行,擴展到 10+ 媒體時會很慢

**當前效能:**
- 2 個媒體 × 3 個 section = 6 次請求
- 每次請求 2-5 秒
- **總時間: 12-30 秒**

**擴展後效能:**
- 10 個媒體 × 3 個 section = 30 次請求
- **總時間: 60-150 秒** ❌ 不可接受

**解決方案:**

```python
import asyncio
import aiohttp

async def fetch_all_sources(sources):
    """並行爬取所有來源"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for source in sources:
            for section in source['sections']:
                tasks.append(fetch_section(session, section))

        results = await asyncio.gather(*tasks)
        return results

# 效能提升:
# 30 次請求 × 3 秒 / 請求 = 90 秒 (同步)
# max(30 次請求) ≈ 5 秒 (並行) ✅
```

### 5. 缺少錯誤監控與告警

**問題:** 爬蟲失敗時只記錄 log,使用者不知道系統是否正常

**風險場景:**
- 選擇器失效 → 無資料 → 沒人發現
- 網站封鎖 → 爬蟲失敗 → 繼續運作但沒輸出
- LLM API 失敗 → fallback 模式 → 草稿品質下降

**必要監控指標:**
```python
class Metrics:
    # 爬蟲健康度
    crawler_success_rate: float  # 應 > 90%
    signals_per_run: int         # 應 > 50

    # 事件偵測
    events_per_run: int          # 正常範圍 0-10
    avg_event_score: float       # 應 > 12

    # LLM 生成
    llm_success_rate: float      # 應 > 95%
    fallback_ratio: float        # 應 < 5%

    def alert_if_abnormal(self):
        """異常時發送告警"""
        if self.crawler_success_rate < 0.9:
            send_alert("爬蟲成功率過低")

        if self.signals_per_run < 20:
            send_alert("採集到的新聞數量異常")
```

### 6. SQLite 擴展性限制

**問題:** SQLite 單檔案,不適合高頻寫入場景

**限制:**
- 寫入時鎖表
- 無法水平擴展
- 併發效能差

**何時需要升級:**
- 監控頻率 < 60 秒
- 監控媒體 > 20 家
- 需要多機部署
- 需要歷史資料分析

**建議:**
- **短期:** 繼續使用 SQLite (實驗階段足夠)
- **中期:** 升級到 PostgreSQL
- **長期:** 考慮 TimescaleDB (時序資料)

### 7. 缺少 Rate Limiting

**問題:** 可能被媒體網站封鎖

**解決方案:**
```python
from ratelimit import limits, sleep_and_retry

class RateLimitedCrawler:
    @sleep_and_retry
    @limits(calls=10, period=60)  # 每分鐘最多 10 次請求
    def fetch(self, url):
        return requests.get(url)
```

### 8. LLM 成本控制

**問題:** 每個事件都呼叫 LLM,成本高

**成本估算:**
- 每次呼叫 ~1000 tokens
- gpt-4o-mini: $0.15 / 1M tokens
- 每小時 10 個事件 × 24 小時 = 240 次呼叫/天
- **成本: $0.036/天** (可接受)

**但如果擴展到 20+ 媒體:**
- 每小時 50 個事件 × 24 小時 = 1200 次呼叫/天
- **成本: $0.18/天 = $5.4/月**

**優化方案:**
```python
# 1. 快取相同事件
if event_exists_in_cache(event_key):
    return get_cached_draft(event_key)

# 2. 只對高分事件生成 LLM 草稿
if event.score < 15:
    return fallback_draft(event)

# 3. 批次生成 (降低 API 呼叫次數)
drafts = batch_generate([event1, event2, event3])
```

---

## ⚠️ 中等優先級問題

### 9. 缺少輸入驗證

**問題:** config.yaml 沒有 schema 驗證

**改進:**
```python
from pydantic import BaseModel, HttpUrl, validator

class SectionConfig(BaseModel):
    section_id: str
    url: HttpUrl
    weight: int
    selectors: List[str]
    max_items: int = 20

    @validator('weight')
    def weight_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('weight must be positive')
        return v
```

### 10. 缺少草稿去重

**問題:** 相同事件可能生成多次草稿

**解決:**
```python
def should_generate_draft(event_key):
    """檢查是否已有近期草稿"""
    recent = db.get_drafts(
        event_key=event_key,
        since=now() - timedelta(hours=6)
    )
    return len(recent) == 0
```

---

## 驗證程式能否運作的必要步驟

我已經建立了完整的驗證工具:

### 1. 快速驗證 (5 分鐘)
```bash
cd /Users/nightpluie/Desktop/newsfollow
./verify.sh
```

這個腳本會:
- ✓ 檢查 Python 環境
- ✓ 建立虛擬環境
- ✓ 安裝依賴套件
- ✓ 驗證設定檔格式
- ✓ 執行爬蟲健康檢查
- ✓ 測試 LLM 整合 (如果有 API key)

### 2. 詳細驗證 (30 分鐘)
參考 `VALIDATION_CHECKLIST.md`,涵蓋:
- Phase 1: 基礎環境
- Phase 2: 爬蟲功能
- Phase 3: 核心功能
- Phase 4: 發布功能
- Phase 5: 持續運作
- Phase 6: 擴展性
- Phase 7: 生產就緒

### 3. 關鍵驗證點

**最重要的 3 個測試:**

```bash
# 1. 爬蟲是否能取得資料
python3 tests/test_crawler_health.py

# 2. 能否偵測事件
python3 main.py run-once
sqlite3 newsfollow.db "SELECT COUNT(*) FROM signals;"
# 應該 > 50

# 3. 能否生成草稿
export OPENAI_API_KEY='your_key'
python3 tests/test_llm_integration.py
```

**如果這 3 個都通過 → 程式基本可運作**

---

## 擴展到更多媒體的建議

### 新增媒體來源的步驟:

1. **先做選擇器探勘:**
```python
# explore_source.py
url = "https://new-media.com/news"
soup = BeautifulSoup(requests.get(url).text, 'html.parser')

# 嘗試不同選擇器
candidates = [
    "a.article-title",
    "h2 a",
    "main a[href*='/news/']",
    ".news-list a"
]

for sel in candidates:
    items = soup.select(sel)
    print(f"{sel}: {len(items)} items")
    for item in items[:3]:
        print(f"  - {item.get_text(strip=True)}")
```

2. **加入 config.yaml:**
```yaml
sources:
  - source_id: new_media
    source_name: NewMedia
    domain_contains: new-media.com
    sections:
      - section_id: homepage
        url: https://new-media.com/news
        weight: 5
        max_items: 20
        selectors:
          - "a.article-title"  # 從探勘結果選最佳的
```

3. **執行健康檢查:**
```bash
python3 tests/test_crawler_health.py
```

4. **實際測試:**
```bash
python3 main.py run-once
python3 main.py list-events --limit 5
```

### 優先加入的媒體建議:

**Tier 1 (重要):**
- 中時電子報
- 自由時報
- 三立新聞

**Tier 2 (次要):**
- 風傳媒
- 蘋果日報
- NOWnews

**選擇標準:**
- 新聞更新頻率高
- 重大新聞報導快
- 網站結構穩定
- 有明確的「即時」或「熱門」區塊

---

## 立即行動建議

### 🚀 Phase 1: 驗證當前系統 (今天)
```bash
./verify.sh
python3 main.py run-once
```

### 🔧 Phase 2: 修復關鍵缺陷 (本週)
1. 加入選擇器健康檢查
2. 加入錯誤告警機制
3. 改用非同步爬蟲 (如果要擴展)

### ✅ Phase 3: 加入測試 (下週)
1. 爬蟲單元測試
2. 聚類演算法測試
3. 端到端測試

### 📦 Phase 4: 重構 (2 週後)
1. 拆分 main.py 成多個模組
2. 加入 pydantic 驗證
3. 改進錯誤處理

### 🎯 Phase 5: 擴展 (1 個月後)
1. 新增 3-5 家媒體
2. 升級到 PostgreSQL (如需要)
3. 加入 dashboard

---

## 總結

**當前狀態:**
- ✅ 核心功能完整
- ✅ 架構設計合理
- ⚠️ 缺少測試和監控
- ⚠️ 擴展性有限

**可以上線嗎?**
- **實驗階段:** ✅ 可以
- **生產環境:** ❌ 需先修復關鍵缺陷

**最快上線路徑:**
1. 執行 `./verify.sh` 確認能運作
2. 加入選擇器健康檢查
3. 設定告警機制 (email/Slack)
4. 小規模測試運作 1 週
5. 觀察指標後決定是否擴展
