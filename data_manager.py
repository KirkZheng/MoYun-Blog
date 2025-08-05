import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional
import threading
from collections import defaultdict

class BlogDataManager:
    def __init__(self, data_file='blog_data.json'):
        self.data_file = data_file
        self.posts = []
        self.lock = threading.Lock()
        self.load_data()
    
    def load_data(self):
        """从JSON文件加载数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.posts = data.get('posts', [])
                    for post in self.posts:
                        if post.get('publish_date'):
                            post['publish_date'] = datetime.fromisoformat(post['publish_date']).date()
            except Exception as e:
                print(f"加载数据失败: {e}")
                self.posts = []
        else:
            self.posts = []
    
    def save_data(self):
        """保存数据到JSON文件"""
        with self.lock:
            try:
                data_to_save = []
                for post in self.posts:
                    post_copy = post.copy()
                    if isinstance(post_copy.get('publish_date'), date):
                        post_copy['publish_date'] = post_copy['publish_date'].isoformat()
                    data_to_save.append(post_copy)
                
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump({'posts': data_to_save}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存数据失败: {e}")
    
    def add_posts_batch(self, posts_list: List[Dict]):
        """批量添加文章"""
        added_count = 0
        with self.lock:
            for post_data in posts_list:
                if not self.post_exists(post_data.get('url')):
                    post_data['id'] = len(self.posts) + 1
                    post_data['created_at'] = datetime.now().isoformat()
                    self.posts.append(post_data)
                    added_count += 1
        return added_count
    
    def post_exists(self, url: str) -> bool:
        """检查文章是否已存在"""
        return any(post.get('url') == url for post in self.posts)
    
    def get_all_posts(self, page: int = 1, per_page: int = 12) -> Dict:
        """获取所有文章（分页）"""
        sorted_posts = sorted(self.posts, key=lambda x: x.get('id', 0), reverse=True)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'posts': sorted_posts[start:end],
            'total': len(sorted_posts),
            'page': page,
            'per_page': per_page,
            'pages': (len(sorted_posts) + per_page - 1) // per_page
        }
    
    def search_posts(self, query: str, page: int = 1, per_page: int = 12) -> Dict:
        """搜索文章"""
        query_lower = query.lower()
        filtered_posts = []
        
        for post in self.posts:
            if (query_lower in post.get('title', '').lower() or 
                query_lower in post.get('content', '').lower() or 
                query_lower in post.get('summary', '').lower()):
                filtered_posts.append(post)
        
        sorted_posts = sorted(filtered_posts, key=lambda x: x.get('id', 0), reverse=True)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'posts': sorted_posts[start:end],
            'total': len(sorted_posts),
            'page': page,
            'per_page': per_page,
            'pages': (len(sorted_posts) + per_page - 1) // per_page
        }
    
    def get_post_by_id(self, post_id: int) -> Optional[Dict]:
        """根据ID获取文章"""
        for post in self.posts:
            if post.get('id') == post_id:
                return post
        return None
    
    def get_date_groups(self) -> List[Dict]:
        """获取按年月分组的文章统计"""
        date_counts = defaultdict(int)
        
        for post in self.posts:
            publish_date = post.get('publish_date')
            if publish_date:
                if isinstance(publish_date, str):
                    publish_date = datetime.fromisoformat(publish_date).date()
                key = (publish_date.year, publish_date.month)
                date_counts[key] += 1
        
        result = []
        for (year, month), count in sorted(date_counts.items(), reverse=True):
            result.append({
                'year': year,
                'month': month,
                'count': count
            })
        
        return result
    
    def get_posts_by_date(self, year: int = None, month: int = None, page: int = 1, per_page: int = 12) -> Dict:
        """按年月获取文章"""
        filtered_posts = []
        
        for post in self.posts:
            publish_date = post.get('publish_date')
            if publish_date:
                if isinstance(publish_date, str):
                    publish_date = datetime.fromisoformat(publish_date).date()
                
                if year and publish_date.year != year:
                    continue
                if month and publish_date.month != month:
                    continue
                
                filtered_posts.append(post)
        
        sorted_posts = sorted(filtered_posts, key=lambda x: x.get('publish_date', date.min), reverse=True)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'posts': sorted_posts[start:end],
            'total': len(sorted_posts),
            'page': page,
            'per_page': per_page,
            'pages': (len(sorted_posts) + per_page - 1) // per_page
        }

# 全局数据管理器实例
data_manager = BlogDataManager()