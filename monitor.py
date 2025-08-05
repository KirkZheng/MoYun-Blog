#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
from models import db, BlogPost
from app import create_app
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import json

def monitor_crawling_progress():
    """监控爬取进度"""
    app = create_app()
    
    with app.app_context():
        while True:
            try:
                # 获取统计信息
                total_posts = BlogPost.query.count()
                
                # 最近24小时新增的文章
                yesterday = datetime.utcnow() - timedelta(days=1)
                recent_posts = BlogPost.query.filter(
                    BlogPost.created_at >= yesterday
                ).count()
                
                # 按日期分组统计
                date_stats = BlogPost.get_date_groups()
                
                # 清屏并显示进度
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("=" * 60)
                print("📊 爬虫进度监控")
                print("=" * 60)
                print(f"📚 总文章数: {total_posts}")
                print(f"🆕 最近24小时新增: {recent_posts}")
                print(f"🎯 目标进度: {total_posts}/1000 ({total_posts/10:.1f}%)")
                
                if total_posts >= 1000:
                    print("✅ 已达成1000篇文章目标！")
                else:
                    remaining = 1000 - total_posts
                    print(f"📈 还需爬取: {remaining} 篇")
                
                print("\n📅 按月份分布:")
                for i, group in enumerate(date_stats[:10]):
                    print(f"  {group.year}年{group.month}月: {group.count} 篇")
                
                if len(date_stats) > 10:
                    print(f"  ... 还有 {len(date_stats) - 10} 个月份")
                
                print(f"\n🕐 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("按 Ctrl+C 退出监控")
                
                # 检查日志文件
                if os.path.exists('crawler.log'):
                    with open('crawler.log', 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            print("\n📝 最新日志:")
                            for line in lines[-5:]:
                                print(f"  {line.strip()}")
                
                time.sleep(10)  # 每10秒更新一次
                
            except KeyboardInterrupt:
                print("\n监控已停止")
                break
            except Exception as e:
                print(f"监控出错: {e}")
                time.sleep(5)

def generate_progress_report():
    """生成爬取进度报告"""
    app = create_app()
    
    with app.app_context():
        total_posts = BlogPost.query.count()
        date_stats = BlogPost.get_date_groups()
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_posts': total_posts,
            'target_achieved': total_posts >= 1000,
            'progress_percentage': (total_posts / 1000) * 100,
            'date_distribution': [
                {
                    'year': group.year,
                    'month': group.month,
                    'count': group.count
                }
                for group in date_stats
            ]
        }
        
        # 保存报告
        with open('crawl_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📊 进度报告已生成: crawl_report.json")
        print(f"📚 总文章数: {total_posts}")
        print(f"🎯 目标完成度: {report['progress_percentage']:.1f}%")
        
        return report

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'report':
        generate_progress_report()
    else:
        monitor_crawling_progress()