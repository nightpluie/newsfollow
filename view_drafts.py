#!/usr/bin/env python3
"""
草稿檢視工具 - 以易讀格式顯示生成的草稿
"""

import argparse
import json
import sqlite3
import sys


def view_drafts(db_path: str, limit: int = 5, event_key: str = None):
    """顯示草稿"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if event_key:
        query = """
            SELECT d.*, e.score, e.source_count, e.signal_count
            FROM drafts d
            LEFT JOIN events e ON d.event_key = e.event_key
            WHERE d.event_key = ?
            ORDER BY d.generated_at DESC
        """
        rows = conn.execute(query, (event_key,)).fetchall()
    else:
        query = """
            SELECT d.*, e.score, e.source_count, e.signal_count
            FROM drafts d
            LEFT JOIN events e ON d.event_key = e.event_key
            ORDER BY d.generated_at DESC
            LIMIT ?
        """
        rows = conn.execute(query, (limit,)).fetchall()

    if not rows:
        print("❌ 沒有找到草稿")
        return

    for i, row in enumerate(rows, 1):
        print("=" * 80)
        print(f"草稿 #{i}")
        print("=" * 80)

        # 基本資訊
        print(f"\n📰 標題: {row['title']}")
        print(f"🔑 Event Key: {row['event_key']}")
        print(f"⏰ 生成時間: {row['generated_at']}")

        if row['score']:
            print(f"📊 評分: {row['score']:.1f} | 媒體數: {row['source_count']} | 訊號數: {row['signal_count']}")

        # 內文
        print(f"\n📝 內文:")
        print("-" * 80)
        print(row['body'])
        print("-" * 80)

        # 圖片提示詞
        print(f"\n🖼️  圖片生成提示:")
        print(row['image_prompt'])

        # 來源
        try:
            sources = json.loads(row['sources_json'])
            if sources:
                print(f"\n🔗 來源 ({len(sources)} 則):")
                for src in sources[:5]:  # 只顯示前 5 個
                    print(f"  • {src['source']}: {src['url']}")
                if len(sources) > 5:
                    print(f"  ... 還有 {len(sources) - 5} 則來源")
        except Exception:
            pass

        # Meta 資訊
        try:
            raw = json.loads(row['raw_json'])
            meta = raw.get('meta', {})
            if meta:
                print(f"\n🏷️  Meta:")
                for key, value in meta.items():
                    print(f"  • {key}: {value}")
        except Exception:
            pass

        print()

    conn.close()


def list_events(db_path: str, limit: int = 20):
    """列出事件"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT event_key, canonical_title, score, source_count, signal_count, last_seen
        FROM events
        ORDER BY score DESC, last_seen DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    if not rows:
        print("❌ 沒有找到事件")
        return

    print("=" * 100)
    print(f"{'評分':<6} {'媒體':<4} {'訊號':<4} {'標題':<60} {'Event Key'}")
    print("=" * 100)

    for row in rows:
        title = row['canonical_title'][:58] + '..' if len(row['canonical_title']) > 60 else row['canonical_title']
        print(
            f"{row['score']:<6.1f} {row['source_count']:<4} {row['signal_count']:<4} {title:<60} {row['event_key']}"
        )

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="草稿檢視工具")
    parser.add_argument("--db", default="./newsfollow.db", help="資料庫路徑")

    sub = parser.add_subparsers(dest="command", required=True)

    # view-drafts 命令
    view = sub.add_parser("view-drafts", help="檢視草稿")
    view.add_argument("--limit", type=int, default=5, help="顯示數量")
    view.add_argument("--event-key", help="指定 event key")

    # list-events 命令
    list_cmd = sub.add_parser("list-events", help="列出事件")
    list_cmd.add_argument("--limit", type=int, default=20, help="顯示數量")

    args = parser.parse_args()

    if args.command == "view-drafts":
        view_drafts(args.db, limit=args.limit, event_key=args.event_key)
    elif args.command == "list-events":
        list_events(args.db, limit=args.limit)


if __name__ == "__main__":
    main()
