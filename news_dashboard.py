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
from concurrent.futures import ThreadPoolExecutor, as_completed
from cache_manager import NewsCache

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # 從 .env 檔案載入環境變數（覆蓋 shell 環境變數）
except ImportError:
    print("⚠️  未安裝 python-dotenv，請執行: pip install python-dotenv")

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

# API Keys 從環境變數讀取
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # 預設使用 gpt-4o-mini

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
    section: str = 'homepage'
    weight: int = 5


class NewsDashboard:
    def __init__(self, config_path: str = "./config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.crawler = RequestsCrawler()
        if not CLAUDE_API_KEY:
            print("⚠️  未設定 ANTHROPIC_API_KEY 環境變數，改寫功能將無法使用")
        self.claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None

        # 初始化混合相似度檢查器（演算法 + LLM）
        self.similarity_checker = HybridSimilarityChecker(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            enable_llm=True
        )

        # 初始化快取管理器（ETtoday 快取 5 分鐘）
        self.cache = NewsCache(cache_dir="./cache", ttl_minutes=5)
        print("✅ 快取系統已啟用（TTL: 5 分鐘）")

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
                        section=sig.section_id,
                        weight=sig.weight,
                    ))

            except Exception as e:
                print(f"Error crawling {source_config['source_id']}/{section['section_id']}: {e}")

        return items

    def crawl_ettoday(self) -> List[NewsItem]:
        """爬取 ETtoday 新聞（帶快取）"""
        # 檢查快取
        cached_data = self.cache.get('ettoday')
        if cached_data:
            cache_info = self.cache.get_info('ettoday')
            print(f"✅ 使用 ETtoday 快取（{cache_info['age_seconds']:.0f}秒前）")
            # 將字典轉回 NewsItem 物件
            return [NewsItem(**item) for item in cached_data]

        print("🔄 爬取 ETtoday 新聞（快取過期或不存在）...")
        items = []

        urls = [
            "https://www.ettoday.net/news/news-list.htm",
            "https://www.ettoday.net/news/focus/焦點新聞/",
            "https://www.ettoday.net/news/hot-news.htm",
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

        # 儲存到快取（轉為字典格式）
        cache_data = [
            {
                'source': item.source,
                'title': item.title,
                'url': item.url,
                'normalized_title': item.normalized_title,
                'crawled_at': item.crawled_at,
                'section': item.section,
                'weight': item.weight,
            }
            for item in unique_items
        ]
        self.cache.set('ettoday', cache_data)
        print(f"💾 已快取 ETtoday 新聞（{len(cache_data)} 則）")

        return unique_items

    def find_missing_news(self, all_source_items: Dict[str, List[NewsItem]],
                         ettoday_items: List[NewsItem]) -> List[Dict]:
        """
        找出 ETtoday 沒有的新聞
        使用混合策略（演算法 + LLM）進行相似度比對
        並將相同新聞分群顯示
        """
        from main import title_similarity
        from news_importance import calculate_news_importance, format_star_rating

        # 收集 ETtoday 所有標題（用於混合比對）
        ettoday_titles_list = [item.title for item in ettoday_items]

        # 收集所有不在 ETtoday 的新聞（使用混合相似度比對）
        self.similarity_checker.reset_statistics()
        missing_items = []

        for source_name, items in all_source_items.items():
            for item in items:
                # 使用混合策略檢查是否在 ETtoday 中存在
                is_in_ettoday = self.similarity_checker.batch_check(
                    candidate_title=item.title,
                    reference_titles=ettoday_titles_list
                )

                # 只有當確定不在 ETtoday 時，才加入缺少列表
                if not is_in_ettoday:
                    missing_items.append(item)

        # 顯示統計資訊
        stats = self.similarity_checker.get_statistics()
        print(f"📊 相似度比對統計: LLM 調用次數 = {stats['llm_call_count']}")

        # 使用改進的相似度演算法進行群集（傳遞性群集）
        clusters = []
        for item in missing_items:
            title = item.title
            placed = False

            # 檢查是否與現有群集中的任何新聞相似
            for i, cluster in enumerate(clusters):
                # 與群集中的每個項目比較
                for existing_item in cluster:
                    # 使用 0.47 閾值（比 0.5 稍低，因為這是最終顯示用）
                    if title_similarity(title, existing_item.title) >= 0.47:
                        clusters[i].append(item)
                        placed = True
                        break
                if placed:
                    break

            if not placed:
                clusters.append([item])

        # 為每個群集建立新聞資訊
        news_by_cluster = []
        for cluster in clusters:
            # 選擇最長的標題作為代表標題
            canonical_title = max((item.title for item in cluster), key=len)
            canonical_url = cluster[0].url

            # 收集所有來源的詳細資訊（使用字典去重）
            sources = []
            source_details_dict = {}
            sections_info = []

            for item in cluster:
                sources.append(item.source)

                # 如果該來源還沒記錄，或新標題更長，則更新
                if item.source not in source_details_dict or len(item.title) > len(source_details_dict[item.source]['title']):
                    source_details_dict[item.source] = {
                        'source': item.source,
                        'title': item.title,
                        'url': item.url,
                    }

                sections_info.append({
                    'source': item.source,
                    'section': getattr(item, 'section', 'homepage'),
                    'weight': getattr(item, 'weight', 5),
                })

            # 將字典轉為列表（每個來源只保留一則）
            source_details = list(source_details_dict.values())

            # 計算重要性評分
            importance = calculate_news_importance(canonical_title, sources, sections_info)
            star_rating = format_star_rating(importance['star_rating'])

            news_by_cluster.append({
                'title': canonical_title,
                'url': canonical_url,
                'normalized_title': cluster[0].normalized_title,
                'crawled_at': cluster[0].crawled_at,
                'sources': sources,  # 簡單的來源名稱列表（用於評分）
                'source_details': source_details,  # 詳細的來源資訊（用於前端顯示，已去重）
                'sections_info': sections_info,
                'importance': importance,
                'star_rating': star_rating,
                'total_score': importance['total_score'],
            })

        # 按重要性評分排序（高分在前）
        news_by_cluster.sort(key=lambda x: x['total_score'], reverse=True)

        return news_by_cluster

    def clean_markdown(self, text: str) -> str:
        """移除 Markdown 格式標記"""
        import re
        # 移除粗體 **text** 或 __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        # 移除斜體 *text* 或 _text_
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # 移除標題標記 #
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        return text

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
1. 嚴格依據素材撰寫 - 只能根據提供的素材,禁止自行揣想或編造
2. 倒金字塔結構 - 最重要資訊在前,依重要性遞減
3. 金字塔原理 - 每段首句是核心論點,後續內容支撐該論點
4. 導言涵蓋 5W1H - 何時、何地、何人、何事、為何、如何
5. 數據先行 - 用具體數字、統計資料開場
6. 250字導言 - 精煉核心重點,不超過250字

【格式要求 - 極度重要】
- 絕對不可使用 Markdown 格式
- 不可使用 **粗體**、*斜體*、# 標題等任何 Markdown 語法
- 使用純文字輸出,不需任何格式標記
- 如需強調,使用「」或直接加強語氣的文字即可
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

                # 清理 Markdown 格式
                clean_title = self.clean_markdown(result.get('title', ''))
                clean_lead = self.clean_markdown(result.get('lead', ''))
                clean_body = self.clean_markdown(result.get('body', ''))

                return {
                    'success': True,
                    'title': clean_title,
                    'lead': clean_lead,
                    'body': clean_body,
                    'original_title': original_title,
                    'original_url': original_url,
                    'model': 'claude-sonnet-4-20250514',
                    'method': 'system_prompt_with_skill',
                }

            except json.JSONDecodeError:
                # 清理 Markdown 格式
                clean_text = self.clean_markdown(response_text)

                return {
                    'success': True,
                    'title': original_title,
                    'lead': clean_text[:250],
                    'body': clean_text,
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
    """爬取所有來源（平行執行）"""
    try:
        # 定義爬取任務
        def crawl_udn():
            config = next((s for s in dashboard.config['sources'] if s['source_id'] == 'udn'), None)
            return ('UDN', dashboard.crawl_source(config) if config else [])

        def crawl_tvbs():
            config = next((s for s in dashboard.config['sources'] if s['source_id'] == 'tvbs'), None)
            return ('TVBS', dashboard.crawl_source(config) if config else [])

        def crawl_chinatimes():
            config = next((s for s in dashboard.config['sources'] if s['source_id'] == 'chinatimes'), None)
            return ('中時新聞網', dashboard.crawl_source(config) if config else [])

        def crawl_setn():
            config = next((s for s in dashboard.config['sources'] if s['source_id'] == 'setn'), None)
            return ('三立新聞網', dashboard.crawl_source(config) if config else [])

        def crawl_et():
            return ('ETtoday', dashboard.crawl_ettoday())

        # 平行爬取所有來源（最多 5 個同時執行）
        results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任務
            futures = [
                executor.submit(crawl_udn),
                executor.submit(crawl_tvbs),
                executor.submit(crawl_chinatimes),
                executor.submit(crawl_setn),
                executor.submit(crawl_et),
            ]

            # 收集結果
            for future in as_completed(futures):
                source_name, items = future.result()
                results[source_name] = items

        # 提取結果
        udn_items = results.get('UDN', [])
        tvbs_items = results.get('TVBS', [])
        chinatimes_items = results.get('中時新聞網', [])
        setn_items = results.get('三立新聞網', [])
        ettoday_items = results.get('ETtoday', [])

        # 組合所有來源的字典
        all_source_items = {
            'UDN': udn_items,
            'TVBS': tvbs_items,
            '中時新聞網': chinatimes_items,
            '三立新聞網': setn_items,
        }

        # 找出 ETtoday 缺少的新聞（使用混合相似度策略）
        missing_news = dashboard.find_missing_news(all_source_items, ettoday_items)

        # 取得 LLM 調用次數統計
        llm_calls = dashboard.similarity_checker.llm_call_count

        return jsonify({
            'success': True,
            'udn': [{'source': i.source, 'title': i.title, 'url': i.url} for i in udn_items],
            'tvbs': [{'source': i.source, 'title': i.title, 'url': i.url} for i in tvbs_items],
            '中時新聞網': [{'source': i.source, 'title': i.title, 'url': i.url} for i in chinatimes_items],
            '三立新聞網': [{'source': i.source, 'title': i.title, 'url': i.url} for i in setn_items],
            'ettoday': [{'source': i.source, 'title': i.title, 'url': i.url} for i in ettoday_items],
            'missing': missing_news,
            'llm_calls': llm_calls,
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
    print("🚀 新聞監控儀表板 v1.1 (Prototype) 啟動中...")
    print("📍 訪問: http://localhost:8080")
    print("=" * 60)
    print("💡 使用方式: System Prompt + 唐鎮宇寫作技能")
    print("   (Skills API 在 Python SDK 中尚未完全支援)")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=8080)
