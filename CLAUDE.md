# 新聞監控系統 - Claude 專案理解文件

這份文件記錄了 Claude 對本專案的理解，用於未來的對話延續和協作。

---

## 📋 專案概述

**專案名稱：** 新聞監控與 AI 改寫系統
**主要目的：** 監控多家新聞媒體，找出其他媒體有報導但 ETtoday 缺少的新聞，並使用 AI 改寫為專業新聞報導
**開發語言：** Python (Flask + BeautifulSoup + Claude API)
**部署方式：** 本地開發伺服器 (http://localhost:8080)

---

## 🏗️ 系統架構

### 核心流程
```
爬取新聞 → 相似度比對 → 重要性評分 → 新聞分群 → AI 改寫
```

### 主要模組

| 模組 | 檔案 | 功能 |
|------|------|------|
| 主程式 | `news_dashboard_with_real_skills.py` | Flask 應用、爬蟲、API 端點 |
| 相似度演算法 | `main.py` | 中文標題相似度比對 (87.5% 準確率) |
| 評分機制 | `news_importance.py` | 新聞重要性評分 (1-5 星) |
| 前端介面 | `templates/dashboard.html` | Web 儀表板 |
| 配置文件 | `config.yaml` | 媒體來源、爬取規則 |

---

## 📡 新聞爬取

### 支援的媒體來源

1. **UDN (聯合新聞網)**
   - Source ID: `udn`
   - Sections: homepage (5), marquee (6), hot (4)
   - Domain: udn.com

2. **TVBS**
   - Source ID: `tvbs`
   - Sections: homepage (5), marquee (6), hot (4)
   - Domain: news.tvbs.com.tw

3. **中時新聞網**
   - Source ID: `chinatimes`
   - Sections: realtime (5), homepage (4)
   - Domain: chinatimes.com

4. **三立新聞網**
   - Source ID: `setn`
   - Sections: viewall (5), homepage (4)
   - Domain: setn.com

5. **ETtoday (基準媒體)**
   - 作為比對基準，找出其他媒體有但 ETtoday 沒有的新聞

### 抓取機制

- **工具：** BeautifulSoup + requests
- **方式：** 配置驅動 (config.yaml)
- **頻率：** 手動觸發（使用者點擊「開始分析」）
- **段落抓取：** 每篇新聞最多抓取 20 段落（用於 AI 改寫）

### 新聞欄位結構

```python
NewsItem:
    - title: str              # 新聞標題
    - url: str                # 新聞連結
    - source: str             # 來源媒體 (UDN, TVBS, etc.)
    - section: str            # Section ID (homepage, marquee, hot)
    - weight: int             # 權重分數 (4-6)
    - normalized_title: str   # 正規化標題（用於比對）
    - crawled_at: str         # 爬取時間
```

---

## 🔍 相似度比對演算法

### 核心函數
`title_similarity(title1, title2)` in `main.py`

### 演算法組成

| 演算法 | 權重 | 說明 |
|--------|------|------|
| Jaccard 相似度 | 35% | 詞彙重疊程度 |
| Cosine 相似度 | 30% | 向量空間相似度 |
| 最長公共子串 (LCS) | 25% | 最長公共連續子字串 |
| 數字匹配 | 10% | 檢查數字是否相同 |

### 比對流程

1. **中文分詞：** 使用 Jieba 分詞
2. **智能實體增強：** 識別台積電、TSMC 等重要實體
3. **綜合計算：** 根據 4 種演算法計算最終分數 (0-1)
4. **閾值判斷：** 相似度 ≥ 0.5 視為同一則新聞

### 關鍵常數

```python
SIMILARITY_THRESHOLD = 0.5  # 相似度閾值
CLUSTER_SIMILARITY = 0.5    # 新聞分群閾值（config.yaml）
```

### 測試結果
- **準確率：** 87.5%
- **能力：** 能正確識別不同措辭但內容相同的新聞

---

## ⭐ 新聞重要性評分

### 評分因素（總分 100 分）

| 因素 | 佔比 | 計分方式 |
|------|------|----------|
| 來源數量 | 40% | 4+ 家=40, 3家=35, 2家=25, 1家=10 |
| 權重分數 | 30% | 累加各來源的 weight 值（最高 18）|
| Section 類型 | 20% | marquee (1.0) > hot (0.8) > homepage (0.6) |
| 標題關鍵字 | 10% | 包含重要關鍵字加分 |
| 特殊關鍵字 | +20 分 | 地震、颱風、總統等重大事件 |

### 星級評分

- ⭐⭐⭐⭐⭐ (5 星)：總分 ≥ 80 分
- ⭐⭐⭐⭐ (4 星)：總分 65-79 分
- ⭐⭐⭐ (3 星)：總分 50-64 分
- ⭐⭐ (2 星)：總分 35-49 分
- ⭐ (1 星)：總分 < 35 分

### 篩選規則

```python
顯示條件:
    - 至少 2 家來源 OR
    - 單一來源但評分 ≥ 60 分
```

### 效果
- **噪音過濾率：** 57%（有效過濾不重要新聞）

---

## 🤖 AI 改寫功能

### 技術架構

| 項目 | 技術 | 說明 |
|------|------|------|
| AI 模型 | Claude Haiku 4.5 | 快速、便宜、適合搭配 Skills |
| API | Claude Skills API | Beta 版本 (skills-2025-10-02) |
| Skill ID | skill_013Hgp6psVYYF7AjWCyPJFNd | 唐鎮宇寫作風格 |
| Skill Path | /Users/nightpluie/Desktop/AI bots/report-tcy | |
| max_tokens | 1500 | 輸出限制 |
| temperature | 0.7 | 生成溫度 |

### 改寫流程

1. **使用者選擇來源：** 勾選要使用的新聞來源（可多選）
2. **抓取完整內容：** 系統抓取每個來源的完整新聞內容（最多 20 段）
3. **綜合改寫：** Claude 根據所有來源的實際內容綜合改寫
4. **輸出結果：** 標題 + 完整內文（純文字格式）

### 改寫規則

```yaml
重要規則:
  - 嚴格根據實際內容撰寫，不得編造或推測
  - 根據素材內容寫完整即可，建議 800 字以內
  - 不使用 Markdown 格式
  - 不在文末署名
  - 直接輸出撰寫結果，不要說明文字
```

### 寫作風格 (唐鎮宇)

- **倒金字塔結構：** 最重要資訊在前，細節在後
- **5W1H 導言：** 何時、何地、何人、何事、為何、如何
- **數據先行：** 用具體數字開場
- **多方聲音：** 官方、專家、業者、當事人
- **人性化收尾：** 以評論、建議或心聲收尾

### 輸出格式

```
標題：（新聞標題）

內文：（完整內文，包含導言）
```

### Token 優化

- **段落限制：** 最多 20 段（智能調整）
- **模型選擇：** Haiku 4.5（成本降低 90%，速度提升 3-5 倍）
- **max_tokens：** 1500（約 800 字）

---

## 🔄 資料處理

### 新聞分群 (Clustering)

**演算法：** Transitive Clustering

```python
# 如果 A 和 B 相似，B 和 C 相似，則 A、B、C 為同一群
相似度閾值: 0.5
```

### 來源去重

**問題：** 同一新聞可能出現在多個 section（homepage、marquee、hot）

**解決方案：**
```python
# 使用 Dictionary 確保每個來源只出現一次
source_details_dict = {}
for item in cluster:
    if item.source not in source_details_dict or len(item.title) > len(source_details_dict[item.source]['title']):
        source_details_dict[item.source] = {
            'source': item.source,
            'title': item.title,
            'url': item.url,
        }
```

### ETtoday 比對

找出其他媒體有但 ETtoday 沒有的新聞：

```python
for news in all_sources:
    is_in_ettoday = False
    for et_news in ettoday_items:
        similarity = title_similarity(news.title, et_news.title)
        if similarity >= 0.5:
            is_in_ettoday = True
            break
    if not is_in_ettoday:
        missing_news.append(news)
```

---

## 📂 專案結構

```
newsfollow/
├── news_dashboard_with_real_skills.py  # 主程式（Flask + 爬蟲 + AI）
├── main.py                              # 相似度演算法
├── news_importance.py                   # 評分機制
├── config.yaml                          # 配置文件
├── newsfollow.db                        # SQLite 資料庫（可選）
├── templates/
│   └── dashboard.html                   # Web 前端
├── .venv/                               # Python 虛擬環境
├── PROJECT_REPORT.html                  # 專案報告（HTML）
└── CLAUDE.md                            # 本文件
```

---

## ⚙️ 配置文件 (config.yaml)

### 主要參數

```yaml
interval_seconds: 180           # 爬取間隔（秒）
cluster_similarity: 0.50        # 新聞分群相似度閾值
crawler_backend: requests       # 爬蟲後端 (requests | openclaw)
database_path: ./newsfollow.db  # 資料庫路徑

llm:
  enabled: true
  provider: openai
  model: gpt-4o-mini            # 配置用，實際使用 Claude
  temperature: 0.4
  max_tokens: 1200

sources:
  - source_id: udn
    source_name: UDN
    domain_contains: udn.com
    sections: [...]
```

---

## 🖥️ API 端點

### Flask Routes

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 渲染 Web 儀表板 |
| `/api/crawl` | POST | 爬取所有媒體新聞 |
| `/api/rewrite` | POST | AI 改寫新聞 |

### `/api/crawl` 回應格式

```json
{
  "success": true,
  "sources": {
    "UDN": 40,
    "TVBS": 38,
    "中時新聞網": 42,
    "三立新聞網": 35
  },
  "ettoday_count": 45,
  "missing": [
    {
      "title": "新聞標題",
      "url": "https://...",
      "sources": ["UDN", "TVBS"],
      "source_details": [
        {"source": "UDN", "title": "...", "url": "..."},
        {"source": "TVBS", "title": "...", "url": "..."}
      ],
      "star_rating": "⭐⭐⭐⭐",
      "total_score": 75.5
    }
  ]
}
```

### `/api/rewrite` 請求格式

```json
{
  "title": "新聞標題",
  "url": "https://...",
  "sources": ["TVBS", "中時新聞網"],
  "normalized_title": "normalized_title_value"
}
```

### `/api/rewrite` 回應格式

```json
{
  "success": true,
  "title": "改寫後的標題",
  "body": "完整內文...",
  "original_title": "原始標題",
  "original_url": "https://...",
  "model": "claude-haiku-4-5-20251001",
  "method": "skills_api",
  "skill_id": "skill_013Hgp6psVYYF7AjWCyPJFNd"
}
```

---

## 🚨 已知問題與解決方案

### 1. Rate Limit 錯誤
**問題：** Claude API 限制 30,000 input tokens / 分鐘
**解決方案：**
- 減少段落數（5 → 20）
- 使用 Haiku 4.5（更快更便宜）
- 減少 max_tokens（2000 → 1500）

### 2. 同一來源出現多次
**問題：** 同一新聞在 homepage、marquee、hot 都出現
**解決方案：**
- 使用 Dictionary 去重
- 選擇標題最長的版本

### 3. Markdown 格式問題
**問題：** Claude 輸出包含 Markdown 格式
**解決方案：**
- Prompt 中明確要求不使用 Markdown
- 後端自動清理 Markdown 格式（`**text**` → `text`）

### 4. 文末署名問題
**問題：** Claude 在文末加上署名（記者XXX/台北報導）
**解決方案：**
- Prompt 中明確要求不署名
- 後端自動移除署名格式

---

## 🛠️ 開發與部署

### 啟動專案

```bash
# 進入專案目錄
cd /Users/nightpluie/Desktop/newsfollow

# 啟動虛擬環境
source .venv/bin/activate

# 啟動 Flask 應用
python news_dashboard_with_real_skills.py

# 訪問 Web 介面
# http://localhost:8080
```

### 停止專案

```bash
# 找到 Python 進程並終止
pkill -f "news_dashboard_with_real_skills.py"
```

### 查看日誌

```bash
tail -f /tmp/dashboard.log
```

---

## 📊 性能指標

| 指標 | 數值 | 說明 |
|------|------|------|
| 相似度準確率 | 87.5% | 能正確識別相同新聞 |
| 噪音過濾率 | 57% | 過濾不重要新聞 |
| API 成本 | Haiku 4.5 | 比 Sonnet 4 便宜 90% |
| 改寫速度 | 3-5 倍 | Haiku vs Sonnet |
| 段落抓取 | 最多 20 段 | 平衡完整性與 token |

---

## 🚀 未來改進方向

### 短期優化
- [ ] 快取機制（減少重複爬取）
- [ ] 錯誤處理優化（網路斷線、爬取失敗）
- [ ] 改寫歷史紀錄

### 中期改進
- [ ] 排程任務（定時自動爬取）
- [ ] 通知系統（重大新聞通知）
- [ ] 更多媒體來源

### 長期規劃
- [ ] 資料視覺化（新聞趨勢分析）
- [ ] 機器學習優化（相似度演算法）
- [ ] 多語言支援

---

## 🔑 關鍵決策記錄

### 為何選擇 Claude Haiku 4.5？
1. **成本考量：** 比 Sonnet 4 便宜 90%
2. **速度優勢：** 3-5 倍更快
3. **Skills 支援：** 與 Skills API 配合良好
4. **質量足夠：** 在有 Skill 指引下，質量可接受

### 為何不使用推測？
**使用者要求：** 不能超出來源內容範圍，必須根據實際內容撰寫
**實作方式：**
- 抓取完整內容（最多 20 段）
- Prompt 明確要求「不得編造或推測」
- 如果抓取失敗，直接返回錯誤

### 為何合併導言和內文？
**使用者偏好：** 簡化輸出格式，不需要分開顯示
**實作方式：**
- Prompt 只要求「標題」和「內文」兩個欄位
- 內文包含完整報導（含導言）

### 為何設定 800 字上限？
**使用者要求：** 主要是內容完整性，字數不是最重要
**實作方式：**
- 建議 800 字以內（非強制）
- 根據素材內容寫完整即可
- max_tokens: 1500（約 800 字）

---

## 📝 重要提醒

### 給未來的 Claude

1. **使用者偏好：**
   - 不要 Markdown 格式
   - 不要文末署名
   - 不要推測或編造
   - 字數完整性 > 字數限制

2. **技術限制：**
   - Claude API Rate Limit: 30,000 tokens/min
   - 段落抓取上限：20 段（平衡 token 使用量）

3. **改動歷史：**
   - 從 15 段 → 5 段 → 20 段（智能調整）
   - 從 Sonnet 4 → Haiku 4.5
   - 從 JSON 格式 → 結構化文本格式
   - 從分開的導言和內文 → 合併的內文

4. **測試建議：**
   - 每次修改後重新測試 AI 改寫功能
   - 確認相似度比對準確率
   - 檢查去重機制是否正常

---

## 📞 聯絡資訊

**專案位置：** `/Users/nightpluie/Desktop/newsfollow`
**Skill 位置：** `/Users/nightpluie/Desktop/AI bots/report-tcy`
**Web 介面：** http://localhost:8080
**日誌位置：** `/tmp/dashboard.log`

---

## 🔄 最新更新（2026-02-08 下午）

### 混合相似度比對策略

**問題：**
- 純演算法比對存在誤判（準確率 87.5%）
- ETtoday 實際有的新聞被誤判為「缺少」

**解決方案：**
- 實作混合策略（演算法 + LLM 兩階段判斷）
- 使用 GPT-4o-mini 處理邊緣案例（0.3-0.6 相似度區間）
- 成本極低：每月約 $1.8

**新增文件：**
- `hybrid_similarity.py` - 混合檢查器核心
- `test_hybrid.py` - 測試腳本
- `HYBRID_SIMILARITY_GUIDE.md` - 完整使用說明
- `.env` - API Keys 配置（已加入 .gitignore）

**準確率提升：**
- 從 87.5% → 預期 95%+
- 誤判率降低 60%

**安全性改進：**
- 所有 API Keys 移到環境變數
- 使用 python-dotenv 載入配置
- 新增 .gitignore 保護敏感文件

---

**最後更新：** 2026-02-08
**版本：** 2.0 (混合策略)
**作者：** Claude Code (Sonnet 4.5) via Happy

---

> 💡 **提示：** 這份文件會隨著專案演進持續更新。如果有重大架構變更，請更新本文件。
