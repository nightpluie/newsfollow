#!/usr/bin/env python3
"""
測試爬蟲 - 檢查中時和三立新聞抓取
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import RequestsCrawler, extract_signals, now_iso
import yaml

def test_source(source_config):
    """測試單一來源"""
    crawler = RequestsCrawler()

    print(f"\n{'='*60}")
    print(f"測試來源: {source_config['source_name']}")
    print(f"{'='*60}")

    total_count = 0

    for section in source_config['sections']:
        print(f"\n📍 Section: {section['section_id']}")
        print(f"   URL: {section['url']}")
        print(f"   Selectors: {section['selectors']}")

        try:
            # 抓取 HTML
            html = crawler.fetch_html(section['url'])
            print(f"   ✅ HTML fetched: {len(html)} bytes")

            # 提取訊號
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

            print(f"   ✅ Signals extracted: {len(signals)}")

            # 顯示前 3 則新聞
            for i, sig in enumerate(signals[:3], 1):
                print(f"      {i}. {sig.title}")
                print(f"         URL: {sig.url}")

            total_count += len(signals)

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n📊 總計: {source_config['source_name']} 抓到 {total_count} 則新聞")
    return total_count

if __name__ == "__main__":
    # 載入配置
    with open('./config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 測試中時新聞網
    chinatimes = next((s for s in config['sources'] if s['source_id'] == 'chinatimes'), None)
    if chinatimes:
        chinatimes_count = test_source(chinatimes)

    # 測試三立新聞網
    setn = next((s for s in config['sources'] if s['source_id'] == 'setn'), None)
    if setn:
        setn_count = test_source(setn)

    print(f"\n{'='*60}")
    print("測試結果總結")
    print(f"{'='*60}")
    print(f"中時新聞網: {chinatimes_count} 則")
    print(f"三立新聞網: {setn_count} 則")
    print(f"\n驗收標準:")
    print(f"  中時: {'✅ PASS' if chinatimes_count >= 15 else '❌ FAIL'} (需要 >= 15)")
    print(f"  三立: {'✅ PASS' if setn_count >= 15 else '❌ FAIL'} (需要 >= 15)")
