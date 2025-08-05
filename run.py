#!/usr/bin/env python3
import subprocess
import sys
import os

def run_crawler():
    """运行爬虫"""
    print("\n开始运行高性能爬虫...")
    try:
        subprocess.run([sys.executable, 'fast_crawler.py'], check=True)
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
        stats = data_manager.get_stats()
        print(f"\n数据统计:")
        print(f"总文章数: {stats['total_posts']}")
        print(f"日期分组数: {stats['date_groups']}")
    except Exception as e:
        print(f"获取统计信息失败: {e}")

def main():
    print("=" * 50)
    print("博客爬虫数据管理系统")
    print("=" * 50)
    
    # 检查是否在正确的目录
    if not os.path.exists('fast_crawler.py'):
        print("错误: 请在项目根目录运行此脚本")
        return
    
    while True:
        print("\n请选择操作:")
        print("1. 运行爬虫")
        print("2. 查看数据统计")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-2): ").strip()
        
        if choice == '1':
            run_crawler()
        elif choice == '2':
            show_stats()
        elif choice == '0':
            print("再见！")
            break
        else:
            print("无效选择，请重新输入")

if __name__ == '__main__':
    main()