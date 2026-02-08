# 🚀 快速開始 - 新聞監控儀表板

## 一鍵啟動

```bash
cd /Users/nightpluie/Desktop/newsfollow
./start_dashboard.sh
```

然後訪問: **http://localhost:5000**

## 使用流程

```
1. 點擊「開始爬取並分析」
   ↓
2. 等待 15-30 秒爬取完成
   ↓
3. 查看「ETtoday 缺少的新聞」
   ↓
4. 點擊「用 Claude 改寫」
   ↓
5. 等待 5-10 秒 AI 生成
   ↓
6. 複製改寫結果使用
```

## 功能說明

| 功能 | 說明 |
|------|------|
| 🔍 **自動爬取** | 抓取 UDN、TVBS、ETtoday 即時新聞 |
| 📊 **智慧比對** | 找出 ETtoday 沒有的新聞 |
| ✍️ **AI 改寫** | Claude API 以唐鎮宇風格改寫 |
| 📝 **即用稿件** | 標題 + 導言 + 內文完整產出 |

## 改寫品質保證

改寫遵循**唐鎮宇寫作原則**:

✅ **倒金字塔結構** - 重要資訊在前
✅ **數據先行** - 具體數字支撐
✅ **5W1H 完整** - 導言涵蓋所有要素
✅ **段落獨立** - 每段首句是核心
✅ **250字導言** - 精煉重點

## 系統要求

- Python 3.8+
- 網路連線
- Claude API Key (已內建)

## 檔案說明

| 檔案 | 用途 |
|------|------|
| `start_dashboard.sh` | 啟動腳本 |
| `news_dashboard.py` | 後端主程式 |
| `templates/dashboard.html` | 前端介面 |
| `config.yaml` | 爬蟲設定 |
| `DASHBOARD_GUIDE.md` | 完整使用說明 |

## 常見問題

### 爬取失敗?
→ 執行 `python3 tests/test_crawler_health.py` 檢查爬蟲狀態

### 改寫失敗?
→ 檢查網路連線和 Claude API 額度

### 找不到缺少的新聞?
→ 可能 ETtoday 報導已很完整,稍後重試

## 進階功能

詳見 `DASHBOARD_GUIDE.md` 了解:
- 自訂爬蟲來源
- 調整改寫風格
- 效能優化
- 安全設定

---

**快速上手,馬上使用! 💪**
