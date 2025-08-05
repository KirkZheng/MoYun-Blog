#!/usr/bin/env python3
import subprocess
import sys
import os

def run_crawler():
    """运行爬虫"""
    print("\n开始运行爬虫...")
    try:
        subprocess.run([sys.executable, 'crawler.py'], check=True)
        print("爬虫运行完成！")
    except subprocess.CalledProcessError as e:
        print(f"爬虫运行失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n爬虫被用户中断")
        return False
    return True

def show_stats():
    """显示文章数据统计"""
    try:
        from data_manager import data_manager
        print(f"\n总文章数: {len(data_manager.posts)}")
    except Exception as e:
        print(f"获取统计信息失败: {e}")

def main():
    print("=" * 40)
    print("博客爬虫系统")
    print("=" * 40)
    
    # 修复：检查crawler.py而不是fast_crawler.py
    if not os.path.exists('crawler.py'):
        print("错误: 请在项目根目录运行此脚本")
        return
    
    while True:
        print("\n1. 运行爬虫")
        print("2. 查看统计")
        print("0. 退出")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            run_crawler()
        elif choice == '2':
            show_stats()
        elif choice == '0':
            print("再见！")
            break
        else:
            print("无效选择")

if __name__ == '__main__':
    main()