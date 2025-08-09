import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional
import threading
from collections import defaultdict
import re
from langdetect import detect
import jieba
from collections import Counter

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
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        try:
            # 清理HTML标签
            clean_text = re.sub(r'<[^>]+>', '', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if len(clean_text) < 10:
                return 'unknown'
            
            lang = detect(clean_text)
            return lang
        except Exception:
            return 'unknown'
    
    def extract_keywords(self, text: str, lang: str = 'zh', top_k: int = 5) -> List[str]:
        """提取关键词"""
        try:
            # 清理HTML标签
            clean_text = re.sub(r'<[^>]+>', '', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if lang == 'zh':
                # 中文分词
                words = jieba.cut(clean_text)
                # 过滤停用词和短词
                stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
                filtered_words = [word for word in words if len(word) > 1 and word not in stop_words and word.strip()]
            else:
                # 英文处理
                words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_text.lower())
                stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
                filtered_words = [word for word in words if word not in stop_words]
            
            # 统计词频
            word_count = Counter(filtered_words)
            return [word for word, count in word_count.most_common(top_k)]
        except Exception:
            return []
    
    def calculate_popularity_score(self, post: Dict) -> float:
        """计算文章热度分数"""
        score = 0.0
        
        # 标题长度权重（适中长度得分更高）
        title_len = len(post.get('title', ''))
        if 10 <= title_len <= 50:
            score += 2.0
        elif 5 <= title_len <= 80:
            score += 1.0
        
        # 内容长度权重
        content_len = len(post.get('content', ''))
        if content_len > 1000:
            score += 3.0
        elif content_len > 500:
            score += 2.0
        elif content_len > 200:
            score += 1.0
        
        # 摘要质量权重
        summary_len = len(post.get('summary', ''))
        if 50 <= summary_len <= 200:
            score += 1.5
        
        # 发布时间权重（越新越高）
        try:
            publish_date = post.get('publish_date')
            if publish_date:
                if isinstance(publish_date, str):
                    publish_date = datetime.fromisoformat(publish_date).date()
                days_ago = (date.today() - publish_date).days
                if days_ago <= 7:
                    score += 3.0
                elif days_ago <= 30:
                    score += 2.0
                elif days_ago <= 90:
                    score += 1.0
        except Exception:
            pass
        
        # 关键词数量权重
        keywords = post.get('keywords', [])
        score += len(keywords) * 0.5
        
        return score
    
    def process_posts_metadata(self):
        """处理文章元数据（语言检测、关键词提取、热度计算）"""
        with self.lock:
            for post in self.posts:
                # 检测语言
                if 'language' not in post:
                    text_to_detect = f"{post.get('title', '')} {post.get('summary', '')}"
                    post['language'] = self.detect_language(text_to_detect)
                
                # 提取关键词
                if 'keywords' not in post:
                    text_for_keywords = f"{post.get('title', '')} {post.get('content', '')}"
                    post['keywords'] = self.extract_keywords(text_for_keywords, post.get('language', 'zh'))
                
                # 计算热度分数
                post['popularity_score'] = self.calculate_popularity_score(post)
    
    def get_filtered_posts(self, filter_english: bool = False, page: int = 1, per_page: int = 12) -> Dict:
        """获取过滤后的文章（可选择过滤纯英文文章）"""
        # 确保元数据已处理
        self.process_posts_metadata()
        
        filtered_posts = self.posts
        
        if filter_english:
            # 过滤掉纯英文文章
            filtered_posts = [post for post in self.posts if post.get('language', 'unknown') != 'en']
        
        # 按热度排序
        sorted_posts = sorted(filtered_posts, key=lambda x: x.get('popularity_score', 0), reverse=True)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'posts': sorted_posts[start:end],
            'total': len(sorted_posts),
            'page': page,
            'per_page': per_page,
            'pages': (len(sorted_posts) + per_page - 1) // per_page
        }
    
    def get_all_posts(self, page: int = 1, per_page: int = 12) -> Dict:
        """获取所有文章（过滤纯英文，按热度排序）"""
        return self.get_filtered_posts(filter_english=True, page=page, per_page=per_page)
    
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

    def get_stats(self) -> Dict:
        """获取博客统计信息"""
        # 确保元数据已处理
        self.process_posts_metadata()
        
        stats = {
            'total_posts': len(self.posts),
            'yearly_stats': {},
            'recent_posts': 0,  # 最近30天
        }
        
        if not self.posts:
            return stats
        
        yearly_count = defaultdict(int)
        recent_count = 0
        
        current_date = date.today()
        
        for post in self.posts:
            # 日期统计
            publish_date = post.get('publish_date')
            if publish_date:
                try:
                    if isinstance(publish_date, str):
                        publish_date = datetime.fromisoformat(publish_date).date()
                    
                    # 年度统计
                    year = publish_date.year
                    yearly_count[year] += 1
                    
                    # 最近30天统计
                    days_diff = (current_date - publish_date).days
                    if days_diff <= 30:
                        recent_count += 1
                        
                except Exception:
                    pass
        
        # 整理统计结果
        stats['yearly_stats'] = dict(yearly_count)
        stats['recent_posts'] = recent_count
        
        return stats
    
    def get_language_distribution(self) -> Dict[str, int]:
        """获取语言分布统计"""
        self.process_posts_metadata()
        language_count = defaultdict(int)
        
        for post in self.posts:
            lang = post.get('language', 'unknown')
            language_count[lang] += 1
        
        return dict(language_count)
    
    def get_monthly_trend(self, months: int = 12) -> List[Dict]:
        """获取月度发布趋势"""
        monthly_count = defaultdict(int)
        
        for post in self.posts:
            publish_date = post.get('publish_date')
            if publish_date:
                try:
                    if isinstance(publish_date, str):
                        publish_date = datetime.fromisoformat(publish_date).date()
                    
                    month_key = f"{publish_date.year}-{publish_date.month:02d}"
                    monthly_count[month_key] += 1
                except Exception:
                    pass
        
        # 获取最近N个月的数据
        sorted_months = sorted(monthly_count.items(), key=lambda x: x[0], reverse=True)[:months]
        
        return [
            {
                'month': month,
                'count': count,
                'year': int(month.split('-')[0]),
                'month_num': int(month.split('-')[1])
            }
            for month, count in sorted_months
        ]
    
    def get_content_analysis(self) -> Dict:
        """获取内容分析统计"""
        self.process_posts_metadata()
        
        analysis = {
            'avg_title_length': 0,
            'avg_content_length': 0,
            'avg_keywords_count': 0,
            'length_distribution': {
                'very_short': 0,  # < 200字
                'short': 0,       # 200-500字
                'medium': 0,      # 500-1500字
                'long': 0,        # 1500-3000字
                'very_long': 0    # > 3000字
            }
        }
        
        if not self.posts:
            return analysis
        
        total_title_len = 0
        total_content_len = 0
        total_keywords = 0
        
        for post in self.posts:
            title_len = len(post.get('title', ''))
            content_len = len(post.get('content', ''))
            keywords_count = len(post.get('keywords', []))
            
            total_title_len += title_len
            total_content_len += content_len
            total_keywords += keywords_count
            
            # 内容长度分布
            if content_len < 200:
                analysis['length_distribution']['very_short'] += 1
            elif content_len < 500:
                analysis['length_distribution']['short'] += 1
            elif content_len < 1500:
                analysis['length_distribution']['medium'] += 1
            elif content_len < 3000:
                analysis['length_distribution']['long'] += 1
            else:
                analysis['length_distribution']['very_long'] += 1
        
        post_count = len(self.posts)
        analysis['avg_title_length'] = round(total_title_len / post_count, 1)
        analysis['avg_content_length'] = round(total_content_len / post_count, 1)
        analysis['avg_keywords_count'] = round(total_keywords / post_count, 1)
        
        return analysis

# 全局数据管理器实例
data_manager = BlogDataManager()