#!/bin/bash
# 一鍵驗證 newsfollow 專案
set -e

echo "======================================================================"
echo "Newsfollow 專案驗證腳本"
echo "======================================================================"

# 檢查 Python 版本
echo ""
echo "[1/6] 檢查 Python 環境..."
python3 --version || { echo "❌ Python 3 未安裝"; exit 1; }
echo "✓ Python 可用"

# 檢查虛擬環境
echo ""
echo "[2/6] 檢查虛擬環境..."
if [ ! -d ".venv" ]; then
    echo "建立虛擬環境..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "✓ 虛擬環境啟動"

# 安裝依賴
echo ""
echo "[3/6] 安裝依賴套件..."
pip install -q -r requirements.txt
echo "✓ 依賴套件已安裝"

# 檢查設定檔
echo ""
echo "[4/6] 檢查設定檔..."
if [ ! -f "config.yaml" ]; then
    echo "複製設定檔範本..."
    cp config.example.yaml config.yaml
fi
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))" || { echo "❌ config.yaml 格式錯誤"; exit 1; }
echo "✓ 設定檔格式正確"

# 檢查環境變數
echo ""
echo "[5/6] 檢查環境變數..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  未設定 OPENAI_API_KEY (LLM 功能將使用 fallback)"
    echo "   export OPENAI_API_KEY='your_key' 來啟用 LLM"
else
    echo "✓ OPENAI_API_KEY 已設定: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4}"
fi

# 執行健康檢查
echo ""
echo "[6/6] 執行爬蟲健康檢查..."
python3 tests/test_crawler_health.py || {
    echo ""
    echo "⚠️  爬蟲健康檢查未完全通過"
    echo "   這可能是因為:"
    echo "   - 網站改版,選擇器需更新"
    echo "   - 網路連線問題"
    echo "   - 網站暫時無法訪問"
    echo ""
    echo "建議:"
    echo "   1. 檢查網路連線"
    echo "   2. 手動訪問 https://udn.com 和 https://news.tvbs.com.tw"
    echo "   3. 如果網站正常但測試失敗,可能需要更新 config.yaml 中的選擇器"
}

# LLM 測試 (可選)
if [ -n "$OPENAI_API_KEY" ]; then
    echo ""
    echo "[額外] 測試 LLM 整合..."
    python3 tests/test_llm_integration.py || {
        echo "⚠️  LLM 測試失敗,將使用 fallback 模式"
    }
fi

echo ""
echo "======================================================================"
echo "驗證完成!"
echo "======================================================================"
echo ""
echo "接下來可以:"
echo "  1. 執行單次監控:  python3 main.py run-once"
echo "  2. 列出事件:      python3 main.py list-events --limit 10"
echo "  3. 循環監控:      python3 main.py loop"
echo ""
echo "詳細驗證清單請參考: VALIDATION_CHECKLIST.md"
