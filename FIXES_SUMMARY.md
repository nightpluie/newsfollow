# 修正總結

## 完成的5大修正

### 1. ✅ 聚焦 ETtoday 缺少的新聞（一眼可見）

**修正前：** 新聞列表需要滑動，缺少的新聞淹沒在表格中

**修正後：**
- 主要區域直接顯示「ETtoday 缺少的新聞」
- 紅色高亮顯示（使用 ETtoday 品牌色 #c4161c）
- 每則新聞獨立卡片，標題+改寫按鈕一起呈現
- 完整新聞列表改為可折疊區域，避免干擾

---

### 2. ✅ 明顯的改寫按鈕（每則新聞旁邊）

**修正前：** 找不到改寫按鈕

**修正後：**
- 每則缺少的新聞右側都有紅色「AI 改寫」按鈕
- 使用 ETtoday 紅色 (#c4161c)
- 按鈕位置固定，不需滑動即可看到
- 一鍵改寫，無需額外操作

---

### 3. ✅ 綜合 UDN + TVBS 內容改寫

**修正前：** 只改寫單一來源內容

**修正後：**
```python
def rewrite_with_claude(self, original_title: str, original_url: str, normalized_title: str = None):
    """使用 Claude Skills API 改寫新聞（綜合 UDN + TVBS 內容）"""

    # 1. 檢查 UDN 是否有相同新聞（根據 normalized_title）
    # 2. 檢查 TVBS 是否有相同新聞
    # 3. 如果兩家都有，抓取完整內容並綜合改寫
    # 4. 傳給 Claude API 改寫成 ETtoday 風格
```

**改寫邏輯：**
- 系統自動識別相同新聞（標題正規化比對）
- 抓取 UDN 完整內容（前 15 段）
- 抓取 TVBS 完整內容（前 15 段）
- 綜合兩家報導，提取最重要資訊
- 使用唐鎮宇寫作技能改寫成 ETtoday 風格

**範例 Prompt:**
```
請綜合以下來自 UDN + TVBS 的報導內容，改寫成 ETtoday 風格的專業報導:

**原始標題:** [標題]

**UDN 報導內容:**
[UDN 完整內容]

**TVBS 報導內容:**
[TVBS 完整內容]

**任務說明:**
1. 綜合 UDN + TVBS 的報導內容，提取最重要的資訊
2. 以 ETtoday 新聞風格重新撰寫
3. 保留所有關鍵數據、時間、人物、事件細節
4. 依倒金字塔結構：最重要資訊在前，細節在後
```

---

### 4. ✅ 修復側邊欄點擊功能

**修正前：** 側邊欄項目無法點擊

**修正後：**
```javascript
// 側邊欄導航
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function() {
        // 切換 active 狀態
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        this.classList.add('active');

        const section = this.getAttribute('data-section');
        console.log('切換到: ' + section);
    });
});
```

**功能：**
- 點擊項目時會切換 active 狀態
- 視覺反饋（高亮顯示）
- 可擴展支援不同頁面

---

### 5. ✅ 改用 ETtoday 紅色識別色

**修正前：** 使用橙色 #ff6b35

**修正後：** 全面改用 ETtoday 官方紅色 #c4161c

**改色範圍：**
- Logo 文字
- 主要按鈕（開始分析、AI 改寫）
- 側邊欄 active 狀態
- 缺少新聞區域標題
- 數量徽章
- Spinner 載入動畫
- 所有強調元素

---

### 6. ✅ 新聞標題直接可點擊

**修正前：** 標題 + 「查看」按鈕（浪費欄位）

**修正後：**
- 標題本身就是連結
- 移除「查看」欄位
- Hover 時標題變紅色並有下劃線
- 節省空間，更直覺

---

## 技術細節

### 前端改進
1. **主次分明佈局**：
   - 主要區域：ETtoday 缺少的新聞（紅色高亮）
   - 次要區域：完整列表（可折疊，預設收起）

2. **視覺層級**：
   - 統計欄：一排橫向顯示
   - 缺少新聞：大卡片，每則新聞獨立
   - 完整列表：緊湊表格，可折疊

3. **互動優化**：
   - 側邊欄可點擊
   - 完整列表可折疊
   - 改寫按鈕明顯
   - 標題直接可點

### 後端改進
1. **快取機制**：
   ```python
   # 快取 UDN 和 TVBS 資料供改寫使用
   dashboard.cached_udn = udn_items
   dashboard.cached_tvbs = tvbs_items
   ```

2. **智能比對**：
   - 根據 `normalized_title` 識別相同新聞
   - 自動抓取多個來源的完整內容
   - 綜合改寫

3. **API 更新**：
   ```python
   @app.route('/api/rewrite', methods=['POST'])
   def api_rewrite():
       """改寫單則新聞（綜合 UDN + TVBS 內容）"""
       normalized_title = data.get('normalized_title', '')
       result = dashboard.rewrite_with_claude(title, url, normalized_title)
   ```

---

## 啟動系統

```bash
cd /Users/nightpluie/Desktop/newsfollow
source .venv/bin/activate
python3 news_dashboard_with_real_skills.py
```

訪問: **http://localhost:8080**

---

## 使用流程

1. **開始分析** - 點擊頂部紅色按鈕
2. **查看統計** - 一排顯示各媒體數量
3. **ET 缺少的新聞** - 主要區域紅色高亮顯示
4. **AI 改寫** - 每則新聞右側紅色按鈕
5. **查看結果** - 彈出視窗顯示標題、導言、內文
6. **完整列表** - 可折疊區域查看所有新聞

---

## 文件位置

- **前端**: `/Users/nightpluie/Desktop/newsfollow/templates/dashboard.html`
- **後端**: `/Users/nightpluie/Desktop/newsfollow/news_dashboard_with_real_skills.py`
- **本文件**: `/Users/nightpluie/Desktop/newsfollow/FIXES_SUMMARY.md`

---

**所有問題已完成修正！系統可以正常使用。**
