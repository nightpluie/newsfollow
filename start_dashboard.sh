#!/bin/bash
# 新聞監控儀表板啟動腳本

echo "======================================================================"
echo "📰 新聞監控儀表板"
echo "======================================================================"
echo ""

# 切換到專案目錄
cd "$(dirname "$0")"

# 啟動虛擬環境
if [ ! -d ".venv" ]; then
    echo "⚠️  虛擬環境不存在,建立中..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# 安裝依賴
echo "📦 檢查依賴套件..."
pip install -q -r requirements_dashboard.txt

echo ""
echo "✅ 準備就緒!"
echo ""
echo "======================================================================"
echo "🌐 儀表板將在以下位址開啟:"
echo "   http://localhost:5000"
echo ""
echo "💡 功能說明:"
echo "   1. 自動爬取 UDN、TVBS、ETtoday 新聞"
echo "   2. 比對找出 ETtoday 缺少的新聞"
echo "   3. 使用 Claude API 以唐鎮宇風格改寫新聞"
echo ""
echo "📌 操作步驟:"
echo "   1. 點擊「開始爬取並分析」按鈕"
echo "   2. 等待爬取完成"
echo "   3. 查看「ETtoday 缺少的新聞」區塊"
echo "   4. 點擊「用 Claude 改寫」自動生成稿件"
echo ""
echo "⌨️  按 Ctrl+C 停止服務"
echo "======================================================================"
echo ""

# 啟動 Flask
python3 news_dashboard.py
