#!/usr/bin/env python3
"""
新聞監控儀表板 - 比對 ETtoday 並用 Claude 改寫
使用 Claude API (含 Skill 支援的 fallback 版本)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List

import anthropic
import requests
import yaml
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# 載入原有的函數
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import (
    RequestsCrawler,
    Signal,
    extract_signals,
    normalize_title,
    now_iso,
)
from hybrid_similarity import HybridSimilarityChecker

app = Flask(__name__)
CORS(app)

# Claude API 設定 (從環境變數讀取)
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 載入寫作技能 (可選)
SKILL_PATH = os.getenv("SKILL_PATH", "./SKILL.md")
TCY_SKILL = ""
if os.path.exists(SKILL_PATH):
    try:
        with open(SKILL_PATH, 'r', encoding='utf-8') as f:
            TCY_SKILL = f.read()
        print(f"✅ 已載入寫作技能: {SKILL_PATH}")
    except Exception as e:
        print(f"⚠️  無法載入技能檔案: {e}")


@dataclass
class NewsItem:
    """新聞項目"""
    source: str
    title: str
    url: str
    normalized_title: str
    crawled_at: str


class NewsDashboard:
    def __init__(self, config_path: str = "./config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.crawler = RequestsCrawler()
        if not CLAUDE_API_KEY:
            print("⚠️  未設定 ANTHROPIC_API_KEY 環境變數，改寫功能將無法使用")
        self.claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None

        # 初始化混合相似度檢查器（演算法 + LLM）
        self.similarity_checker = HybridSimilarityChecker(enable_llm=True)
        print("✅ 混合相似度檢查器已啟用（演算法 + GPT-4o-mini）")

    def crawl_source(self, source_config: Dict) -> List[NewsItem]:
        """爬取單一媒體來源"""
        items = []

        for section in source_config['sections']:
            try:
                html = self.crawler.fetch_html(section['url'])
                signals = extract_signals(
                    html=html,
                    base_url=section['url'],
                    source_id=source_config['source_id'],
                    source_name=source_config['source_name'],
                    section_id=section['section_id'],
                    domain_contains=source_config.get('domain_contains', ''),
                    selectors=section.get('selectors', []),
                    weight=section.get('weight', 1),
                    crawled_at=now_iso(),
                    max_items=section.get('max_items', 20),
                )

                for sig in signals:
                    items.append(NewsItem(
                        source=sig.source_name,
                        title=sig.title,
                        url=sig.url,
                        normalized_title=sig.normalized_title,
                        crawled_at=sig.crawled_at,
                    ))

            except Exception as e:
                print(f"Error crawling {source_config['source_id']}/{section['section_id']}: {e}")

        return items

    def crawl_ettoday(self) -> List[NewsItem]:
        """爬取 ETtoday 新聞"""
        items = []

        urls = [
            "https://www.ettoday.net/news/news-list.htm",
            "https://www.ettoday.net/news/focus/focus-list.htm",
        ]

        for url in urls:
            try:
                html = self.crawler.fetch_html(url)
                soup = BeautifulSoup(html, 'html.parser')

                selectors = [
                    "h3 a",
                    ".part_list_2 h3 a",
                    ".piece h3 a",
                ]

                for selector in selectors:
                    for link in soup.select(selector):
                        title = link.get_text(strip=True)
                        href = link.get('href', '')

                        if not title or len(title) < 8:
                            continue

                        full_url = href if href.startswith('http') else f"https://www.ettoday.net{href}"

                        items.append(NewsItem(
                            source="ETtoday",
                            title=title,
                            url=full_url,
                            normalized_title=normalize_title(title),
                            crawled_at=now_iso(),
                        ))

            except Exception as e:
                print(f"Error crawling ETtoday {url}: {e}")

        # 去重
        seen = set()
        unique_items = []
        for item in items:
            key = item.normalized_title
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        return unique_items

    def find_missing_news(self, udn_items: List[NewsItem], tvbs_items: List[NewsItem],
                         ettoday_items: List[NewsItem]) -> List[Dict]:
        """
        找出 ETtoday 沒有的新聞
        使用混合策略（演算法 + LLM）進行相似度比對
        """
        # 收集 ETtoday 所有標題（用於混合比對）
        ettoday_titles_list = [item.title for item in ettoday_items]
        all_items = udn_items + tvbs_items

        # 重置統計資訊
        self.similarity_checker.reset_statistics()

        missing = []
        for item in all_items:
            # 使用混合策略檢查是否在 ETtoday 中存在
            is_in_ettoday = self.similarity_checker.batch_check(
                candidate_title=item.title,
                reference_titles=ettoday_titles_list
            )

            # 只有當確定不在 ETtoday 時，才加入缺少列表
            if not is_in_ettoday:
                # 避免重複（檢查是否已在 missing 列表中）
                if not any(m['normalized_title'] == item.normalized_title for m in missing):
                    missing.append({
                        'source': item.source,
                        'title': item.title,
                        'url': item.url,
                        'normalized_title': item.normalized_title,
                        'crawled_at': item.crawled_at,
                    })

        # 顯示統計資訊
        stats = self.similarity_checker.get_statistics()
        print(f"📊 相似度比對統計: LLM 調用次數 = {stats['llm_call_count']}")

        return missing

    def rewrite_with_claude(self, original_title: str, original_url: str) -> Dict:
        """使用 Claude API 改寫新聞 (使用唐鎮宇技能指引)"""
        try:
            # 先嘗試抓取原文內容
            try:
                html = self.crawler.fetch_html(original_url)
                soup = BeautifulSoup(html, 'html.parser')
                paragraphs = soup.find_all('p')
                original_content = '\n'.join([p.get_text(strip=True) for p in paragraphs[:10]])
            except:
                original_content = ""

            # 準備包含唐鎮宇技能的 system prompt
            system_prompt = f"""你是一位專業的新聞記者。請嚴格遵循以下唐鎮宇的新聞報導寫作技能:

{TCY_SKILL}

重要提醒:
1. **嚴格依據素材撰寫** - 只能根據提供的素材,禁止自行揣想或編造
2. **倒金字塔結構** - 最重要資訊在前,依重要性遞減
3. **金字塔原理** - 每段首句是核心論點,後續內容支撐該論點
4. **導言涵蓋 5W1H** - 何時、何地、何人、何事、為何、如何
5. **數據先行** - 用具體數字、統計資料開場
6. **250字導言** - 精煉核心重點,不超過250字
"""

            user_prompt = f"""請將以下新聞改寫成 ETtoday 風格的專業報導:

**原始標題:** {original_title}
**原始來源:** {original_url}

**原始內容:**
{original_content if original_content else "（無法取得完整內容,請根據標題推測並改寫,但請明確標示為推測內容）"}

請提供:
1. 新聞標題 (簡潔有力,50字以內)
2. 導言 (250字以內,涵蓋 5W1H,數據先行)
3. 完整內文 (依倒金字塔結構,約 400-600 字)

請以 JSON 格式回傳:
{{
    "title": "改寫後的標題",
    "lead": "導言內容 (250字內)",
    "body": "完整內文 (400-600字)"
}}
"""

            # 呼叫 Claude API
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # 解析回應
            response_text = message.content[0].text

            # 嘗試提取 JSON
            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                result = json.loads(response_text.strip())

                return {
                    'success': True,
                    'title': result.get('title', ''),
                    'lead': result.get('lead', ''),
                    'body': result.get('body', ''),
                    'original_title': original_title,
                    'original_url': original_url,
                    'model': 'claude-sonnet-4-20250514',
                    'method': 'system_prompt_with_skill',
                }

            except json.JSONDecodeError:
                return {
                    'success': True,
                    'title': original_title,
                    'lead': response_text[:250],
                    'body': response_text,
                    'original_title': original_title,
                    'original_url': original_url,
                    'model': 'claude-sonnet-4-20250514',
                    'method': 'system_prompt_with_skill',
                    'note': 'Failed to parse JSON, returning raw text',
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'original_title': original_title,
                'original_url': original_url,
            }


# 建立全域實例
dashboard = NewsDashboard()


@app.route('/')
def index():
    """首頁"""
    return render_template('dashboard.html')


@app.route('/api/crawl', methods=['POST'])
def api_crawl():
    """爬取所有來源"""
    try:
        udn_config = next((s for s in dashboard.config['sources'] if s['source_id'] == 'udn'), None)
        udn_items = dashboard.crawl_source(udn_config) if udn_config else []

        tvbs_config = next((s for s in dashboard.config['sources'] if s['source_id'] == 'tvbs'), None)
        tvbs_items = dashboard.crawl_source(tvbs_config) if tvbs_config else []

        ettoday_items = dashboard.crawl_ettoday()

        missing_news = dashboard.find_missing_news(udn_items, tvbs_items, ettoday_items)

        return jsonify({
            'success': True,
            'udn': [{'source': i.source, 'title': i.title, 'url': i.url} for i in udn_items],
            'tvbs': [{'source': i.source, 'title': i.title, 'url': i.url} for i in tvbs_items],
            'ettoday': [{'source': i.source, 'title': i.title, 'url': i.url} for i in ettoday_items],
            'missing': missing_news,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/rewrite', methods=['POST'])
def api_rewrite():
    """改寫單則新聞"""
    try:
        data = request.json
        title = data.get('title', '')
        url = data.get('url', '')

        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400

        result = dashboard.rewrite_with_claude(title, url)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)

    print("=" * 60)
    print("🚀 新聞監控儀表板啟動中...")
    print("📍 訪問: http://localhost:8080")
    print("=" * 60)
    print("💡 使用方式: System Prompt + 唐鎮宇寫作技能")
    print("   (Skills API 在 Python SDK 中尚未完全支援)")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=8080)
