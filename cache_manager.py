#!/usr/bin/env python3
"""簡單的新聞快取管理器"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

class NewsCache:
    """新聞快取管理器（檔案型）"""

    def __init__(self, cache_dir: str = "./cache", ttl_minutes: int = 5):
        """
        初始化快取管理器

        Args:
            cache_dir: 快取目錄
            ttl_minutes: 快取有效時間（分鐘）
        """
        self.cache_dir = cache_dir
        self.ttl = timedelta(minutes=ttl_minutes)
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        """取得快取檔案路徑"""
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """
        取得快取資料

        Args:
            key: 快取鍵值（例如：'ettoday'）

        Returns:
            快取資料，若不存在或過期則回傳 None
        """
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 檢查是否過期
            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            if datetime.now() - cached_at > self.ttl:
                # 過期，刪除快取
                os.remove(cache_path)
                return None

            return cache_data['data']

        except Exception as e:
            print(f"⚠️  讀取快取失敗 ({key}): {e}")
            return None

    def set(self, key: str, data: List[Dict[str, Any]]) -> bool:
        """
        設定快取資料

        Args:
            key: 快取鍵值
            data: 要快取的資料

        Returns:
            成功回傳 True，失敗回傳 False
        """
        cache_path = self._get_cache_path(key)

        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'data': data,
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"⚠️  寫入快取失敗 ({key}): {e}")
            return False

    def clear(self, key: Optional[str] = None):
        """
        清除快取

        Args:
            key: 指定鍵值清除，None 則清除全部
        """
        if key:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                print(f"✅ 已清除快取: {key}")
        else:
            # 清除全部快取
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("✅ 已清除所有快取")

    def get_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        取得快取資訊（不回傳資料）

        Args:
            key: 快取鍵值

        Returns:
            快取資訊（cached_at, age, is_valid）
        """
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            age = datetime.now() - cached_at
            is_valid = age <= self.ttl

            return {
                'cached_at': cache_data['cached_at'],
                'age_seconds': age.total_seconds(),
                'is_valid': is_valid,
                'items_count': len(cache_data['data']),
            }

        except Exception as e:
            print(f"⚠️  讀取快取資訊失敗 ({key}): {e}")
            return None


# 測試
if __name__ == '__main__':
    cache = NewsCache(ttl_minutes=5)

    # 測試寫入
    test_data = [
        {'title': '測試新聞1', 'url': 'https://example.com/1'},
        {'title': '測試新聞2', 'url': 'https://example.com/2'},
    ]

    print("測試寫入快取...")
    cache.set('test', test_data)

    # 測試讀取
    print("\n測試讀取快取...")
    cached = cache.get('test')
    print(f"讀取結果: {len(cached) if cached else 0} 則新聞")

    # 測試資訊
    print("\n測試快取資訊...")
    info = cache.get_info('test')
    if info:
        print(f"快取時間: {info['cached_at']}")
        print(f"快取年齡: {info['age_seconds']:.1f} 秒")
        print(f"是否有效: {info['is_valid']}")
        print(f"項目數量: {info['items_count']}")

    # 測試清除
    print("\n測試清除快取...")
    cache.clear('test')
