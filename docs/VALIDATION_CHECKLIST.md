# Newsfollow 驗證檢查清單

## Phase 1: 基礎環境驗證

### 1.1 依賴套件安裝
```bash
cd /Users/nightpluie/Desktop/newsfollow
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**驗證點:**
- [ ] 所有套件安裝成功
- [ ] BeautifulSoup4, requests, pyyaml 版本相容

### 1.2 設定檔驗證
```bash
cp config.example.yaml config.yaml
# 檢查設定檔格式
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

**驗證點:**
- [ ] YAML 格式正確
- [ ] 所有必要欄位存在

### 1.3 LLM API 驗證
```bash
export OPENAI_API_KEY='your_key'
export OPENAI_MODEL='gpt-4o-mini'

# 測試 API 連線
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**驗證點:**
- [ ] API key 有效
- [ ] 模型可用

## Phase 2: 爬蟲功能驗證

### 2.1 UDN 爬蟲測試
```python
# test_udn_crawler.py
import requests
from bs4 import BeautifulSoup

url = "https://udn.com/news/index"
resp = requests.get(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36"
})

soup = BeautifulSoup(resp.text, "html.parser")

# 測試選擇器
selectors = [
    "a.story-list__title-link",
    ".story-list a",
    "main a[href*='/news/story/']"
]

for sel in selectors:
    items = soup.select(sel)
    print(f"{sel}: {len(items)} items")
```

**驗證點:**
- [ ] UDN 網站可訪問
- [ ] 至少一個選擇器返回 > 5 個結果
- [ ] 提取的標題合理 (8-80 字元)

### 2.2 TVBS 爬蟲測試
```python
# test_tvbs_crawler.py
import requests
from bs4 import BeautifulSoup

url = "https://news.tvbs.com.tw/"
resp = requests.get(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36"
})

soup = BeautifulSoup(resp.text, "html.parser")

selectors = [
    "a.news__title",
    "a[href*='news.tvbs.com.tw/'][title]",
    "main a[href*='news.tvbs.com.tw/']"
]

for sel in selectors:
    items = soup.select(sel)
    print(f"{sel}: {len(items)} items")
```

**驗證點:**
- [ ] TVBS 網站可訪問
- [ ] 至少一個選擇器返回 > 5 個結果
- [ ] URL 格式正確 (news.tvbs.com.tw)

### 2.3 選擇器健康度檢查
**預期結果:**
- UDN 每個 section 應返回 10-20 條新聞
- TVBS 每個 section 應返回 10-20 條新聞
- 如果返回 < 5 條,選擇器可能已失效

## Phase 3: 核心功能驗證

### 3.1 執行單次監控 (不發布)
```bash
python3 main.py run-once
```

**驗證點:**
- [ ] 程式正常執行完成
- [ ] 輸出包含 signals 數量 (預期 > 50)
- [ ] 輸出包含 events 數量 (預期 0-5)
- [ ] 產生 newsfollow.db 檔案

### 3.2 檢查資料庫
```bash
sqlite3 newsfollow.db "SELECT COUNT(*) FROM signals;"
sqlite3 newsfollow.db "SELECT COUNT(*) FROM events;"
sqlite3 newsfollow.db "SELECT canonical_title, score FROM events ORDER BY score DESC LIMIT 5;"
```

**驗證點:**
- [ ] signals 表有資料 (預期 > 50 筆)
- [ ] events 表有資料 (如果有重大新聞)
- [ ] score 計算合理 (11-25 分範圍)

### 3.3 列出事件
```bash
python3 main.py list-events --limit 10
```

**驗證點:**
- [ ] 顯示最近事件
- [ ] 時間戳記格式正確
- [ ] canonical_title 是中文新聞標題

### 3.4 LLM 草稿生成驗證
```bash
# 檢查草稿表
sqlite3 newsfollow.db "SELECT event_key, title, LENGTH(body) as body_len FROM drafts ORDER BY generated_at DESC LIMIT 3;"
```

**驗證點:**
- [ ] drafts 表有資料
- [ ] title 欄位有內容
- [ ] body 長度合理 (> 100 字元)
- [ ] 不是 fallback 草稿 (沒有 "[PROTOTYPE DRAFT" 前綴)

## Phase 4: 發布功能驗證

### 4.1 測試 Stub Publisher
```bash
python3 main.py run-once --publish
```

**驗證點:**
- [ ] 程式正常執行
- [ ] publish_logs 表有資料
- [ ] status 為 "stubbed"

### 4.2 測試 Command Publisher
**建立測試腳本:**
```python
# test_publisher.py
import sys
import json

draft = json.load(sys.stdin)
print(json.dumps({
    "status": "ok",
    "external_id": "test_123",
    "message": f"Published: {draft['title']}"
}))
```

**修改 config.yaml:**
```yaml
publisher:
  mode: command
  publish_command: "python3 test_publisher.py"
```

**執行:**
```bash
python3 main.py run-once --publish
```

**驗證點:**
- [ ] 程式正常執行
- [ ] publish_logs 表有 status="ok" 記錄
- [ ] external_id 正確

## Phase 5: 持續運作驗證

### 5.1 循環模式測試 (短時間)
```bash
# 修改 config.yaml: interval_seconds: 30
timeout 120 python3 main.py loop
```

**驗證點:**
- [ ] 每 30 秒執行一次
- [ ] 可用 Ctrl+C 中斷
- [ ] 沒有記憶體洩漏

### 5.2 錯誤恢復測試
**模擬網路錯誤:**
- 修改 config.yaml 加入無效 URL
- 執行 `python3 main.py run-once`

**驗證點:**
- [ ] 程式不會崩潰
- [ ] 記錄錯誤到 log
- [ ] 其他來源正常處理

## Phase 6: 擴展性驗證

### 6.1 新增媒體來源
**修改 config.yaml 加入第三個媒體:**
```yaml
sources:
  - source_id: test_source
    source_name: TEST
    domain_contains: example.com
    sections:
      - section_id: homepage
        url: https://example.com/news
        weight: 5
        max_items: 10
        selectors:
          - "a[href]"
```

**驗證點:**
- [ ] 程式接受新設定
- [ ] 新來源資料正確儲存
- [ ] 跨媒體聚類正常運作

### 6.2 效能基準測試
```bash
time python3 main.py run-once
```

**驗證點:**
- [ ] 執行時間 < 30 秒 (兩個媒體)
- [ ] 記憶體使用 < 200MB
- [ ] CPU 使用合理

## Phase 7: 生產就緒檢查

### 7.1 必要功能
- [ ] 環境變數設定正確
- [ ] 資料庫路徑可寫入
- [ ] Log 輸出正常
- [ ] 錯誤處理完善

### 7.2 建議改進 (優先級)
**P0 (必須):**
- [ ] 加入選擇器失效偵測
- [ ] 加入爬蟲成功率監控
- [ ] 加入 LLM 呼叫重試機制

**P1 (重要):**
- [ ] 改用非同步爬蟲
- [ ] 加入 rate limiting
- [ ] 加入草稿去重機制

**P2 (建議):**
- [ ] 改用 PostgreSQL
- [ ] 加入告警系統
- [ ] 加入 dashboard

## 驗證完成標準

✅ **可以上線:**
- Phase 1-4 全部通過
- 至少連續運作 1 小時無錯誤
- 成功偵測到 3+ 個真實事件
- LLM 草稿品質可接受

⚠️ **需要改進:**
- 選擇器失效率 > 20%
- 爬蟲失敗率 > 10%
- 誤報事件 > 50%

🔴 **不可上線:**
- 爬蟲完全失效
- 資料庫寫入失敗
- LLM 呼叫全部失敗
- 程式頻繁崩潰
