#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
from data_manager import data_manager
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import json

def monitor_crawling_progress():
    """监控爬取进度"""
    while True:
        try:
            # 获取统计信息
            stats = data_manager.get_stats()
            total_posts = stats['total_posts']
            date_groups = data_manager.get_date_groups()
            
            # 清屏并显示进度
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 60)
            print("📊 爬虫进度监控")
            print("=" * 60)
            print(f"📚 总文章数: {total_posts}")
            print(f"🎯 目标进度: {total_posts}/1000 ({total_posts/10:.1f}%)")
            
            if total_posts >= 1000:
                print("✅ 已达成1000篇文章目标！")
            else:
                remaining = 1000 - total_posts
                print(f"📈 还需爬取: {remaining} 篇")
            
            print("\n📅 按月份分布:")
            for i, group in enumerate(date_groups[:10]):
                print(f"  {group['year']}年{group['month']}月: {group['count']} 篇")
            
            print("\n⏰ 监控时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print("\n按 Ctrl+C 退出监控")
            
            time.sleep(5)  # 每5秒刷新一次
            
        except KeyboardInterrupt:
            print("\n👋 监控已停止")
            break
        except Exception as e:
            print(f"❌ 监控出错: {e}")
            time.sleep(10)

def generate_progress_report():
    """生成进度报告"""
    try:
        stats = data_manager.get_stats()
        date_groups = data_manager.get_date_groups()
        
        report = {
            "生成时间": datetime.now().isoformat(),
            "总文章数": stats['total_posts'],
            "完成度": f"{stats['total_posts']/10:.1f}%",
            "按月分布": [
                {
                    "年月": f"{group['year']}-{group['month']:02d}",
                    "文章数": group['count']
                }
                for group in date_groups
            ]
        }
        
        # 保存报告
        with open('progress_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print("📊 进度报告已生成: progress_report.json")
        
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'report':
        generate_progress_report()
    else:
        monitor_crawling_progress()