import json
import os
from datetime import datetime
import threading
from collections import namedtuple

# 分页结果对象
PaginationResult = namedtuple('PaginationResult', ['posts', 'page', 'pages', 'per_page', 'total', 'has_prev', 'has_next', 'prev_num', 'next_num', 'iter_pages'])

class BlogDataManager:
    def __init__(self, data_file='blog_data.json'):
        self.data_file = data_file
        self.posts = []
        self.lock = threading.Lock()
        self.load_data()
    
    def load_data(self):
        """加载数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.posts = data.get('posts', [])
                    print(f"已加载 {len(self.posts)} 篇文章")
            except Exception as e:
                print(f"加载数据失败: {e}")
                self.posts = []
        else:
            self.posts = []
    
    def save_data(self):
        """保存数据"""
        with self.lock:
            try:
                data = {'posts': self.posts}
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存数据失败: {e}")
    
    def add_post(self, post):
        """添加文章"""
        with self.lock:
            # 检查是否已存在
            if not self.post_exists(post.get('url', '')):
                post['id'] = len(self.posts) + 1
                post['created_at'] = datetime.now().isoformat()
                self.posts.append(post)
                return True
            return False
    
    def batch_add_posts(self, posts_list):
        """批量添加文章"""
        added_count = 0
        for post in posts_list:
            if self.add_post(post):
                added_count += 1
        if added_count > 0:
            self.save_data()
        return added_count
    
    def post_exists(self, url):
        """检查文章是否已存在"""
        return any(post.get('url') == url for post in self.posts)
    
    def get_all_posts(self, page=1, per_page=12):
        """获取所有文章（分页）"""
        # 按创建时间倒序排列
        sorted_posts = sorted(self.posts, key=lambda x: x.get('created_at', ''), reverse=True)
        
        total = len(sorted_posts)
        start = (page - 1) * per_page
        end = start + per_page
        posts_page = sorted_posts[start:end]
        
        pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < pages
        prev_num = page - 1 if has_prev else None
        next_num = page + 1 if has_next else None
        
        def iter_pages():
            for num in range(1, pages + 1):
                yield num
        
        return PaginationResult(
            posts=posts_page,
            page=page,
            pages=pages,
            per_page=per_page,
            total=total,
            has_prev=has_prev,
            has_next=has_next,
            prev_num=prev_num,
            next_num=next_num,
            iter_pages=iter_pages
        )
    
    def search_posts(self, query, page=1, per_page=12):
        """搜索文章"""
        query = query.lower()
        filtered_posts = []
        
        for post in self.posts:
            title = post.get('title', '').lower()
            content = post.get('content', '').lower()
            summary = post.get('summary', '').lower()
            
            if query in title or query in content or query in summary:
                filtered_posts.append(post)
        
        # 按创建时间倒序排列
        sorted_posts = sorted(filtered_posts, key=lambda x: x.get('created_at', ''), reverse=True)
        
        total = len(sorted_posts)
        start = (page - 1) * per_page
        end = start + per_page
        posts_page = sorted_posts[start:end]
        
        pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < pages
        prev_num = page - 1 if has_prev else None
        next_num = page + 1 if has_next else None
        
        def iter_pages():
            for num in range(1, pages + 1):
                yield num
        
        return PaginationResult(
            posts=posts_page,
            page=page,
            pages=pages,
            per_page=per_page,
            total=total,
            has_prev=has_prev,
            has_next=has_next,
            prev_num=prev_num,
            next_num=next_num,
            iter_pages=iter_pages
        )
    
    def get_post_by_id(self, post_id):
        """根据ID获取文章"""
        for post in self.posts:
            if post.get('id') == post_id:
                return post
        return None

# 全局数据管理器实例
data_manager = BlogDataManager()