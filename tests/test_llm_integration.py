#!/usr/bin/env python3
"""
LLM 整合測試
驗證 OpenAI API 連線和草稿生成功能
"""

import json
import os
import sys

import requests


def test_openai_api() -> bool:
    """測試 OpenAI API 連線"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("❌ 未設定 OPENAI_API_KEY 環境變數")
        return False

    print(f"✓ API Key: {api_key[:10]}...{api_key[-4:]}")

    # 測試 API 連線
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    print(f"✓ Base URL: {base_url}")
    print(f"✓ Model: {model}")

    # 建立測試請求
    payload = {
        "model": model,
        "temperature": 0.4,
        "max_tokens": 100,
        "messages": [
            {"role": "system", "content": "You are a test assistant. Return JSON only."},
            {
                "role": "user",
                "content": 'Return this JSON: {"test": "ok", "timestamp": "2024-01-01"}',
            },
        ],
    }

    try:
        resp = requests.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        print(f"✓ API 回應: {content[:100]}")

        return True

    except Exception as exc:
        print(f"❌ API 呼叫失敗: {exc}")
        return False


def test_draft_generation() -> bool:
    """測試草稿生成功能"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return False

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # 模擬事件資料
    mock_event = {
        "event_key": "evt_test123",
        "canonical_title": "台北市長宣布新政策",
        "score": 15.5,
        "reasons": ["base_weight=10", "source_bonus=3", "volume_bonus=2"],
        "signals": [
            {
                "source": "UDN",
                "section": "homepage",
                "title": "台北市長今宣布新政策 影響百萬市民",
                "url": "https://udn.com/news/story/1234/5678",
            },
            {
                "source": "TVBS",
                "section": "marquee",
                "title": "北市新政策出爐 市長:將改善交通問題",
                "url": "https://news.tvbs.com.tw/politics/9999",
            },
        ],
    }

    style_prompt = (
        "Write in concise breaking-news style for Taiwan digital media. "
        "Lead with key development, keep source attributions, no speculation."
    )

    system_prompt = (
        "You are a newsroom assistant. Return strict JSON with keys: "
        "headline, article, image_prompt. No markdown, no extra keys."
    )

    user_prompt = (
        f"Style requirement: {style_prompt}\n"
        "Task: synthesize cross-source event draft for ETtoday workflow.\n"
        "Input event JSON:\n"
        f"{json.dumps(mock_event, ensure_ascii=False)}"
    )

    payload = {
        "model": model,
        "temperature": 0.4,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        resp = requests.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]

        # 解析 JSON
        parsed = parse_json_block(content)
        if not isinstance(parsed, dict):
            print(f"❌ LLM 未返回有效 JSON: {content[:200]}")
            return False

        if "headline" not in parsed or "article" not in parsed:
            print(f"❌ JSON 缺少必要欄位: {list(parsed.keys())}")
            return False

        print("✓ 草稿生成成功:")
        print(f"  標題: {parsed.get('headline', '')[:60]}")
        print(f"  內文: {parsed.get('article', '')[:100]}...")
        print(f"  圖片: {parsed.get('image_prompt', '')[:60]}")

        return True

    except Exception as exc:
        print(f"❌ 草稿生成失敗: {exc}")
        return False


def parse_json_block(text: str):
    """解析 LLM 返回的 JSON (可能包含 markdown)"""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except Exception:
                return None
    return None


def main() -> int:
    print("=" * 80)
    print("LLM 整合測試")
    print("=" * 80)

    print("\n[1/2] 測試 OpenAI API 連線...")
    if not test_openai_api():
        return 1

    print("\n[2/2] 測試草稿生成功能...")
    if not test_draft_generation():
        return 1

    print("\n" + "=" * 80)
    print("✅ LLM 整合測試通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
