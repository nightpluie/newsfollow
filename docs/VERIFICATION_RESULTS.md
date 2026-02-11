# Newsfollow 驗證結果報告

**驗證時間:** 2026-02-08 08:13
**測試配置:** 降低門檻 (threshold: 4, similarity: 0.60)

---

## ✅ 驗證成功項目

### 1. 爬蟲功能
- **UDN 首頁**: ✅ 正常運作 (67 個項目)
  - 選擇器 `a.story-list__title-link` 已失效
  - 但 fallback 選擇器運作良好
- **TVBS**: ⚠️ 部分運作 (20 個項目)
  - 大多數選擇器失效
  - Generic fallback 勉強運作

**收集成果:**
- 總訊號數: 84
- UDN: 32 (homepage: 20, marquee: 12)
- TVBS: 52 (homepage: 20, hot: 20, marquee: 12)

### 2. 事件偵測
- **偵測事件數**: 49 個
- **評分範圍**: 4.0 - 10.0
- **聚類運作**: ✅ 正常

**高分事件 (10 分):**
1. 生於林宅血案年代！賈永婕怒「隻手遮天」太殘暴 (5 個訊號)
2. 高雄透天厝奪命惡火 (5 個訊號)
3. 天氣寒流警報 (5 個訊號)

### 3. 草稿生成
- **生成草稿數**: 58 篇
- **模式**: Fallback (因無 OPENAI_API_KEY)
- **草稿結構**: ✅ 完整

**草稿包含:**
- ✅ 標題 (event canonical title)
- ✅ 內文 (cross-source highlights)
- ✅ 圖片生成提示詞
- ✅ 來源列表

### 4. 資料庫儲存
- **Runs 表**: ✅ 記錄執行歷程
- **Signals 表**: ✅ 84 筆訊號
- **Events 表**: ✅ 49 個事件
- **Drafts 表**: ✅ 58 篇草稿
- **Event_signals 關聯**: ✅ 正常

---

## ⚠️ 發現的問題

### 1. 選擇器失效 (嚴重)

**UDN:**
- `a.story-list__title-link` ❌ 完全失效
- `https://udn.com/rank/pv` ❌ 404 錯誤

**TVBS:**
- `a.news__title` ❌ 失效
- `a[href*='news.tvbs.com.tw/'][title]` ❌ 失效
- `.hot a`, `.popular a` ❌ 失效

**影響:**
- 只能依賴 generic fallback 選擇器
- 採集效率降低
- 可能遺漏重要新聞

**建議修復:**
```yaml
# 更新 config.yaml 的選擇器
sources:
  - source_id: udn
    sections:
      - section_id: homepage
        selectors:
          - ".story-list a"  # 保留這個
          - "main a[href*='/news/story/']"  # 保留這個
          - "article a[href*='/news/']"  # 新增通用選擇器
```

### 2. 無跨媒體事件

**觀察:**
- 所有事件的 `source_count = 1` (單一媒體)
- 沒有 UDN + TVBS 同時報導的新聞

**原因:**
- 測試時間點可能沒有重大突發新聞
- 兩家媒體報導角度不同
- 相似度門檻可能需調整

**正常情況下:**
- 重大新聞會被多家媒體報導
- 會產生 `source_count = 2+` 的事件
- 評分會更高 (15-25 分)

### 3. LLM 未啟用

**狀態:**
- 所有草稿使用 fallback 模式
- 標題前綴: `[Prototype]`
- 內文: 簡單的來源列表

**如要啟用 LLM:**
```bash
export OPENAI_API_KEY='sk-proj-...'
export OPENAI_MODEL='gpt-4o-mini'
python3 main.py run-once
```

**預期 LLM 草稿:**
- 專業新聞標題
- 結構化內文 (導言 + 發展 + 來源)
- 精確的圖片生成提示

---

## 📊 驗證統計

| 指標 | 數值 | 狀態 |
|------|------|------|
| 爬蟲成功率 | 83% (5/6) | ⚠️ 可接受 |
| 訊號收集數 | 84 | ✅ 正常 |
| 事件偵測數 | 49 | ✅ 正常 (降低門檻) |
| 草稿生成率 | 100% | ✅ 正常 |
| 跨媒體事件 | 0 | ⚠️ 需觀察 |
| LLM 成功率 | 0% | ❌ 未設定 API |

---

## 🎯 結論

### 程式能否運作？
**✅ 可以運作**

核心功能都正常:
- 爬蟲能採集新聞
- 聚類演算法運作
- 草稿生成正常
- 資料庫儲存完整

### 但需要改進:

**P0 (立即修復):**
1. 更新失效的 CSS 選擇器
2. 修復 UDN 熱門頁面 URL

**P1 (重要):**
1. 設定 OPENAI_API_KEY 啟用 LLM
2. 加入選擇器健康度監控
3. 調整相似度門檻以捕捉跨媒體事件

**P2 (建議):**
1. 改用非同步爬蟲 (擴展時)
2. 加入 rate limiting
3. 加入錯誤告警

---

## 🔧 如何查看結果

### 方式 1: 使用檢視工具 (推薦)

```bash
cd /Users/nightpluie/Desktop/newsfollow
source .venv/bin/activate

# 列出事件
python3 view_drafts.py list-events --limit 20

# 查看草稿
python3 view_drafts.py view-drafts --limit 5

# 查看特定事件的草稿
python3 view_drafts.py view-drafts --event-key evt_d14729ce66cc0645
```

### 方式 2: 直接查詢資料庫

```bash
# 查看所有事件
sqlite3 newsfollow.db "SELECT canonical_title, score FROM events ORDER BY score DESC LIMIT 10;"

# 查看草稿
sqlite3 newsfollow.db "SELECT title FROM drafts LIMIT 10;"

# 查看詳細草稿
sqlite3 newsfollow.db "SELECT title, body FROM drafts WHERE event_key='evt_xxx';"
```

### 方式 3: 使用內建命令

```bash
# 列出最近事件
python3 main.py list-events --limit 20

# 再執行一次監控
python3 main.py run-once
```

---

## 📝 實際草稿範例

### 高分事件草稿 (10 分)

**標題:** 生於林宅血案年代！賈永婕怒「隻手遮天」太殘暴：當權者給交代

**內文:**
```
[PROTOTYPE DRAFT | OPENAI_API_KEY missing]
Event: 生於林宅血案年代！賈永婕怒「隻手遮天」太殘暴：當權者給交代

Cross-source highlights:
- TVBS (marquee): 生於林宅血案年代！賈永婕罕動怒「太殘暴」：當權者給交代
- TVBS (marquee): 生於林宅血案年代！賈永婕怒「隻手遮天」太殘暴：當權者給交代
- TVBS (homepage): 生於林宅血案年代！賈永婕罕動怒「太殘暴」：當權者給交代
- TVBS (homepage): 生於林宅血案年代！賈永婕怒「隻手遮天」太殘暴：當權者給交代
- TVBS (hot): 生於林宅血案年代！賈永婕怒「隻手遮天」太殘暴：當權者給交代

This is a placeholder draft. Connect your production LLM prompt for final tone/style.
```

**圖片提示:** news photo style, realistic, no logos, depict the core event context inferred from title

**來源:**
- TVBS: https://news.tvbs.com.tw/...

---

## 🚀 下一步建議

### 立即行動 (今天)
1. ✅ 驗證完成 - 程式可運作
2. 📝 閱讀此報告了解現狀
3. 🔧 決定是否啟用 LLM (設定 API key)

### 短期改進 (本週)
1. 更新 config.yaml 中失效的選擇器
2. 修復 UDN 熱門頁面 URL
3. 設定 OPENAI_API_KEY 測試真實草稿品質

### 中期計畫 (2 週內)
1. 加入選擇器健康度自動監控
2. 觀察跨媒體事件偵測情況
3. 調整評分與相似度參數

### 長期規劃 (1 個月)
1. 新增 3-5 家媒體來源
2. 實作非同步爬蟲
3. 加入 dashboard 和告警系統

---

**報告結束**

如有問題,可使用以下命令:
- `./verify.sh` - 重新驗證環境
- `python3 tests/test_crawler_health.py` - 檢查爬蟲健康度
- `python3 view_drafts.py list-events` - 查看事件列表
