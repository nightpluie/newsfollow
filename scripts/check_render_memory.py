#!/usr/bin/env python3
"""
檢查 Render 環境記憶體使用
在 Render 上執行: python check_render_memory.py
"""

import psutil
import os

def check_memory():
    process = psutil.Process()
    mem_info = process.memory_info()

    print("=" * 60)
    print("記憶體使用情況")
    print("=" * 60)
    print(f"RSS (實際使用): {mem_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS (虛擬記憶體): {mem_info.vms / 1024 / 1024:.2f} MB")

    # 系統記憶體
    vm = psutil.virtual_memory()
    print(f"\n系統記憶體:")
    print(f"總計: {vm.total / 1024 / 1024:.2f} MB")
    print(f"可用: {vm.available / 1024 / 1024:.2f} MB")
    print(f"使用率: {vm.percent}%")

    # Render 免費方案限制
    RENDER_FREE_LIMIT = 512
    current_usage = mem_info.rss / 1024 / 1024

    print(f"\nRender 免費方案限制: {RENDER_FREE_LIMIT} MB")
    print(f"當前使用: {current_usage:.2f} MB")
    print(f"剩餘空間: {RENDER_FREE_LIMIT - current_usage:.2f} MB")

    if current_usage > RENDER_FREE_LIMIT * 0.8:
        print("\n⚠️  警告：記憶體使用超過 80% 限制！")
        print("   建議升級 Render 方案或優化記憶體使用")

    return current_usage

if __name__ == "__main__":
    check_memory()
