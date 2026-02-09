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
            model=OPENAI_MODEL,  # 使用環境變數配置的模型（預設 gpt-4.1-nano）
            enable_llm=True,
            timeout=10  # API 請求超時 10 秒（防止單次請求卡住）
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
                    exclude_patterns=source_config.get('exclude_patterns', []),
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
        from main import title_similarity, compute_title_features
        from news_importance import calculate_news_importance, format_star_rating

        # 預計算 ETtoday 所有標題特徵（用於混合比對）
        # 這能大幅減少重複建立 Set/Counter 的記憶體開銷
        ettoday_features_list = [compute_title_features(item.title) for item in ettoday_items]

        # 收集所有不在 ETtoday 的新聞（使用混合相似度比對）
        self.similarity_checker.reset_statistics()
        missing_items = []

        # 用於群集的項目列表（儲存 (item, features)）
        missing_items_with_features = []

        for source_name, items in all_source_items.items():
            for item in items:
                # 預計算候選標題特徵
                candidate_features = compute_title_features(item.title)
                
                # 使用混合策略檢查是否在 ETtoday 中存在
                # 傳遞預計算的特徵物件
                is_in_ettoday = self.similarity_checker.batch_check(
                    candidate_title=candidate_features,
                    reference_titles=ettoday_features_list
                )

                # 只有當確定不在 ETtoday 時，才加入缺少列表
                if not is_in_ettoday:
                    missing_items.append(item)
                    missing_items_with_features.append((item, candidate_features))

        # 顯示統計資訊
        stats = self.similarity_checker.get_statistics()
        print(f"📊 相似度比對統計: LLM 調用次數 = {stats['llm_call_count']}")

        # 使用改進的相似度演算法進行群集（傳遞性群集）
        # clusters 儲存結構: List[List[Tuple[NewsItem, TitleFeatures]]]
        clusters = []
        for item, features in missing_items_with_features:
            placed = False

            # 檢查是否與現有群集中的任何新聞相似
            for i, cluster in enumerate(clusters):
                # 與群集中的每個項目比較
                for existing_item, existing_features in cluster:
                    # 使用 0.47 閾值（比 0.5 稍低，因為這是最終顯示用）
                    # 直接使用特徵進行比對
                    if title_similarity(features, existing_features) >= 0.47:
                        clusters[i].append((item, features))
                        placed = True
                        break
                if placed:
                    break

            if not placed:
                clusters.append([(item, features)])
        
        # 還原 clusters 為純 NewsItem 列表以便後續處理
        news_clusters = [[pair[0] for pair in cluster] for cluster in clusters]

        # 為每個群集建立新聞資訊
        news_by_cluster = []
        for cluster in news_clusters:
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

    def rewrite_with_claude(self, original_title: str, original_url: str, sources_data: List[Dict] = None) -> Dict:
        """使用 Claude API 改寫新聞 (根據勾選的多個來源綜合改寫)"""
        try:
            # 如果沒有提供 sources_data，回傳錯誤
            if not sources_data or len(sources_data) == 0:
                return {
                    'success': False,
                    'error': '請至少勾選一個新聞來源',
                    'original_title': original_title,
                    'original_url': original_url,
                }

            # 抓取所有勾選來源的完整內容
            all_sources_content = []
            for source_info in sources_data:
                source_name = source_info.get('source', '未知來源')
                source_title = source_info.get('title', '')
                source_url = source_info.get('url', '')

                try:
                    html = self.crawler.fetch_html(source_url)
                    soup = BeautifulSoup(html, 'html.parser')
                    paragraphs = soup.find_all('p')
                    # 抓取最多 20 段
                    content_paragraphs = [p.get_text(strip=True) for p in paragraphs[:20] if p.get_text(strip=True)]
                    full_content = '\n\n'.join(content_paragraphs)

                    if full_content:
                        all_sources_content.append({
                            'source': source_name,
                            'title': source_title,
                            'url': source_url,
                            'content': full_content,
                        })
                    else:
                        # 如果抓取失敗，記錄但繼續
                        all_sources_content.append({
                            'source': source_name,
                            'title': source_title,
                            'url': source_url,
                            'content': '（無法取得完整內容）',
                        })
                except Exception as e:
                    print(f"⚠️  抓取 {source_name} 內容失敗: {e}")
                    all_sources_content.append({
                        'source': source_name,
                        'title': source_title,
                        'url': source_url,
                        'content': f'（抓取失敗: {str(e)}）',
                    })

            # 如果所有來源都抓取失敗，回傳錯誤
            valid_sources = [s for s in all_sources_content if '（無法取得完整內容）' not in s['content'] and '（抓取失敗' not in s['content']]
            if len(valid_sources) == 0:
                return {
                    'success': False,
                    'error': '所有來源的內容都無法取得，無法進行改寫',
                    'original_title': original_title,
                    'original_url': original_url,
                }

            # 準備包含唐鎮宇技能的 system prompt
            system_prompt = f"""你是一位專業的新聞記者。請嚴格遵循以下唐鎮宇的新聞報導寫作技能:

{TCY_SKILL}

【核心原則 - 絕對嚴格遵守】
1. 絕對依據素材撰寫 - 只能根據提供的新聞來源內容改寫，不得添加任何原文沒有的資訊
2. 禁止推測或編造 - 如果原文沒有提到的事情，絕對不要寫出來
3. 禁止使用不具體的消息來源 - 不可使用「據了解」、「消息人士表示」、「有關人士指出」、「據悉」等模糊來源
4. 內容必須可追溯 - 改寫的每一句話都必須能在提供的來源中找到對應的原文
5. 不要延伸或推論 - 只改寫文字，不增加任何解釋、分析或延伸內容

【寫作技巧】
1. 倒金字塔結構 - 最重要資訊在前，依重要性遞減
2. 金字塔原理 - 每段首句是核心論點，後續內容支撐該論點
3. 5W1H 導言 - 何時、何地、何人、何事、為何、如何
4. 數據先行 - 用具體數字、統計資料開場（如果原文有提供）
5. 多方聲音 - 如果原文有引述不同人的說法，要保留這些引述

【格式要求】
- 絕對不可使用 Markdown 格式
- 不可使用 **粗體**、*斜體*、# 標題等任何 Markdown 語法
- 使用純文字輸出，不需任何格式標記
- 如需強調，使用「」或直接加強語氣的文字即可

【禁止事項 - 極度重要】
❌ 不可添加原文沒有的數據、時間、地點、人名
❌ 不可使用「據了解」、「消息人士」、「有關人士」等不具體來源
❌ 不可推測事件的原因、影響或未來發展（除非原文有明確提到）
❌ 不可編造任何引述或對話
❌ 不可添加任何背景資訊（除非原文有提供）
"""

            # 整理所有來源內容
            sources_text = ""
            for idx, source_data in enumerate(all_sources_content, 1):
                sources_text += f"\n{'='*60}\n"
                sources_text += f"來源 {idx}: {source_data['source']}\n"
                sources_text += f"標題: {source_data['title']}\n"
                sources_text += f"網址: {source_data['url']}\n"
                sources_text += f"\n完整內容:\n{source_data['content']}\n"

            user_prompt = f"""請根據以下 {len(all_sources_content)} 個新聞來源的實際內容，綜合改寫成一篇 ETtoday 風格的專業報導。

{sources_text}

{'='*60}

【改寫要求】
1. 標題：簡潔有力，50 字以內，必須基於上述來源內容
2. 內文：完整報導，建議 800 字以內
   - 使用倒金字塔結構
   - 每個資訊都必須能在上述來源中找到對應內容
   - 如果多個來源有不同說法，可以綜合呈現
   - 絕對不要添加來源沒有的資訊

【重要提醒】
- 改寫時只能重新組織和潤飾上述來源的內容
- 不可添加任何上述來源沒有提到的資訊
- 不可使用「據了解」、「消息人士」等不具體來源
- 每句話都必須有明確的來源依據

請直接提供改寫後的標題和內文，不需要任何說明文字。

格式如下：
標題：（改寫後的標題）

內文：（完整內文）
"""

            # 呼叫 Claude API
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.3,  # 降低 temperature 減少創造性，增加事實性
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # 解析回應
            response_text = message.content[0].text.strip()

            # 解析標題和內文
            title = ""
            body = ""

            if "標題：" in response_text or "標題:" in response_text:
                # 提取標題
                title_match = response_text.split("標題：" if "標題：" in response_text else "標題:")[1].split("\n")[0].strip()
                title = title_match

                # 提取內文
                if "內文：" in response_text:
                    body = response_text.split("內文：")[1].strip()
                elif "內文:" in response_text:
                    body = response_text.split("內文:")[1].strip()
            else:
                # 如果沒有明確標記，使用原標題
                title = original_title
                body = response_text

            # 清理 Markdown 格式
            clean_title = self.clean_markdown(title)
            clean_body = self.clean_markdown(body)

            return {
                'success': True,
                'title': clean_title,
                'body': clean_body,
                'original_title': original_title,
                'original_url': original_url,
                'sources_used': [s['source'] for s in all_sources_content],
                'model': 'claude-sonnet-4-20250514',
                'method': 'multi_source_rewrite',
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
    import time
    start_time = time.time()
    print(f"\n{'='*60}", flush=True)
    print(f"🚀 開始分析流程 (時間戳: {time.strftime('%Y-%m-%d %H:%M:%S')})", flush=True)
    print(f"{'='*60}", flush=True)

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

        # 平行爬取所有來源（最多 2 個同時執行，減少記憶體壓力）
        results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
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

        # 主動回收記憶體（釋放 BeautifulSoup 解析產生的大量物件）
        import gc
        gc.collect()

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
        print(f"\n⏱️  階段 1 完成（爬取）: {time.time() - start_time:.2f} 秒")
        print(f"📊 爬取結果統計:")
        for source, items in all_source_items.items():
            print(f"   - {source}: {len(items)} 則")
        print(f"   - ETtoday: {len(ettoday_items)} 則")

        print(f"\n🔍 階段 2 開始（相似度比對）...")
        stage2_start = time.time()

        missing_news = dashboard.find_missing_news(all_source_items, ettoday_items)

        print(f"⏱️  階段 2 完成（比對）: {time.time() - stage2_start:.2f} 秒")

        # 取得 LLM 調用次數統計
        llm_calls = dashboard.similarity_checker.llm_call_count
        print(f"📊 LLM 調用統計: {llm_calls} 次")

        total_time = time.time() - start_time
        print(f"\n✅ 分析完成！總耗時: {total_time:.2f} 秒", flush=True)
        print(f"   - 找到缺少新聞: {len(missing_news)} 則", flush=True)
        print(f"{'='*60}\n", flush=True)

        return jsonify({
            'success': True,
            'udn': [{'source': i.source, 'title': i.title, 'url': i.url} for i in udn_items],
            'tvbs': [{'source': i.source, 'title': i.title, 'url': i.url} for i in tvbs_items],
            '中時新聞網': [{'source': i.source, 'title': i.title, 'url': i.url} for i in chinatimes_items],
            '三立新聞網': [{'source': i.source, 'title': i.title, 'url': i.url} for i in setn_items],
            'ettoday': [{'source': i.source, 'title': i.title, 'url': i.url} for i in ettoday_items],
            'missing': missing_news,
            'llm_calls': llm_calls,
            'total_time': f"{total_time:.2f}s",
        })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"\n❌ 錯誤發生:")
        print(error_detail)
        print(f"{'='*60}\n")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
        }), 500


@app.route('/api/rewrite', methods=['POST'])
def api_rewrite():
    """改寫單則新聞（根據勾選的多個來源）"""
    try:
        data = request.json
        title = data.get('title', '')
        url = data.get('url', '')
        sources = data.get('sources', [])  # 勾選的來源列表

        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400

        if not sources or len(sources) == 0:
            return jsonify({'success': False, 'error': '請至少勾選一個新聞來源'}), 400

        # 呼叫改寫函數，傳入勾選的來源
        result = dashboard.rewrite_with_claude(title, url, sources)
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
