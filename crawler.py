import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, date
import re
from urllib.parse import urljoin, urlparse, parse_qs
# 删除: from models import db, BlogPost
# 删除: from app import create_app
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Set, Dict
import random
from data_manager import data_manager  # 添加这行

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedBlogCrawler:
    def __init__(self, base_url, target_count=1000, max_workers=5):
        self.base_url = base_url
        self.target_count = target_count
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 爬取状态
        self.crawled_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.posts_count = 0
        self.lock = threading.Lock()
        
        # 用户代理轮换
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
    def get_random_delay(self, min_delay=1, max_delay=3):
        """获取随机延迟时间"""
        return random.uniform(min_delay, max_delay)
    
    def rotate_user_agent(self):
        """轮换用户代理"""
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    def get_page_content(self, url, retries=3):
        """获取页面内容，带重试机制"""
        for attempt in range(retries):
            try:
                self.rotate_user_agent()
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                # 检查是否被重定向到错误页面
                if '404' in response.url or 'error' in response.url.lower():
                    logger.warning(f"页面可能不存在: {url}")
                    return None
                    
                return response.text
            except requests.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{retries}): {url} - {e}")
                if attempt < retries - 1:
                    time.sleep(self.get_random_delay(2, 5))
                else:
                    logger.error(f"最终请求失败: {url}")
                    with self.lock:
                        self.failed_urls.add(url)
        return None
    
    def extract_date(self, date_text):
        """提取日期"""
        if not date_text:
            return date.today()
            
        # 更多日期格式支持
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})',
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # 英文日期格式
        ]
        
        # 月份名称映射
        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if groups[1].isalpha():  # 英文月份
                            day, month_name, year = groups
                            month = month_names.get(month_name.lower())
                            if month:
                                return date(int(year), month, int(day))
                        elif len(groups[0]) == 4:  # 年在前
                            year, month, day = map(int, groups)
                        else:  # 年在后
                            if '年' in date_text:
                                year, month, day = map(int, groups)
                            else:
                                month, day, year = map(int, groups)
                        return date(year, month, day)
                except (ValueError, TypeError):
                    continue
        
        return date.today()
    
    def generate_summary(self, content, max_length=200):
        """生成文章摘要"""
        # 清理HTML标签和多余空白
        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        if len(clean_content) <= max_length:
            return clean_content
        
        # 尝试在句号处截断
        sentences = re.split(r'[。！？.!?]', clean_content)
        summary = ''
        for sentence in sentences:
            if len(summary + sentence + '。') <= max_length:
                summary += sentence + '。'
            else:
                break
        
        if not summary:
            summary = clean_content[:max_length] + '...'
        
        return summary
    
    def discover_pagination_urls(self, html_content, base_url):
        """发现分页链接"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = set()
        
        # 多种分页链接模式
        pagination_patterns = [
            # Blogger常见分页
            {'tag': 'a', 'attrs': {'class': re.compile(r'blog-pager-older-link|older-posts')}},
            {'tag': 'a', 'text': re.compile(r'older|next|下一页|更多|继续阅读', re.I)},
            
            # 数字分页
            {'tag': 'a', 'attrs': {'class': re.compile(r'page-numbers|pagination')}},
            
            # 通用分页
            {'tag': 'a', 'href': re.compile(r'page|p=|start=|offset=', re.I)},
        ]
        
        for pattern in pagination_patterns:
            if 'text' in pattern:
                links = soup.find_all(pattern['tag'], text=pattern['text'])
            elif 'href' in pattern:
                links = soup.find_all(pattern['tag'], href=pattern['href'])
            else:
                links = soup.find_all(pattern['tag'], pattern.get('attrs', {}))
            
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
        
        # 尝试构造数字分页URL
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        
        # Blogger分页参数
        if 'blogspot.com' in base_url:
            for i in range(2, 51):  # 尝试前50页
                page_url = f"{base_url}?max-results=20&start={20*(i-1)}"
                urls.add(page_url)
        
        return urls
    
    def discover_archive_urls(self, html_content, base_url):
        """发现归档链接"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = set()
        
        # 查找归档链接
        archive_patterns = [
            {'tag': 'a', 'href': re.compile(r'archive|\d{4}/\d{2}|\d{4}_\d{2}', re.I)},
            {'tag': 'a', 'text': re.compile(r'\d{4}年|\d{4}/\d{2}|archive', re.I)},
            {'tag': 'a', 'attrs': {'class': re.compile(r'archive|date', re.I)}},
        ]
        
        for pattern in archive_patterns:
            if 'text' in pattern:
                links = soup.find_all(pattern['tag'], text=pattern['text'])
            elif 'href' in pattern:
                links = soup.find_all(pattern['tag'], href=pattern['href'])
            else:
                links = soup.find_all(pattern['tag'], pattern.get('attrs', {}))
            
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
        
        return urls
    
    def parse_blog_posts(self, html_content, page_url):
        """解析博客文章"""
        soup = BeautifulSoup(html_content, 'html.parser')
        posts = []
        
        # 多种文章容器模式
        post_selectors = [
            'div.post',
            'article',
            'div.entry',
            'div[class*="post"]',
            'div.blog-post',
            'div.hentry',
            '.post-outer',
            '.post-body',
        ]
        
        post_containers = []
        for selector in post_selectors:
            containers = soup.select(selector)
            if containers:
                post_containers = containers
                logger.info(f"使用选择器 '{selector}' 找到 {len(containers)} 个文章容器")
                break
        
        if not post_containers:
            logger.warning(f"未找到文章容器: {page_url}")
            return posts
        
        for i, container in enumerate(post_containers):
            try:
                post_data = {}
                
                # 提取标题 - 多种模式
                title_selectors = [
                    'h1.post-title', 'h2.post-title', 'h3.post-title',
                    'h1.entry-title', 'h2.entry-title', 'h3.entry-title',
                    '.post-title a', '.entry-title a',
                    'h1', 'h2', 'h3'
                ]
                
                title_elem = None
                for selector in title_selectors:
                    title_elem = container.select_one(selector)
                    if title_elem:
                        break
                
                title = title_elem.get_text().strip() if title_elem else f'无标题_{i+1}'
                if len(title) > 500:  # 标题过长可能是误识别
                    title = title[:500] + '...'
                post_data['title'] = title
                
                # 提取内容 - 多种模式
                content_selectors = [
                    '.post-body', '.entry-content', '.post-content',
                    '.content', '.post-text', '.entry-text'
                ]
                
                content_elem = None
                for selector in content_selectors:
                    content_elem = container.select_one(selector)
                    if content_elem:
                        break
                
                if not content_elem:
                    content_elem = container
                
                # 清理内容
                if content_elem:
                    # 移除脚本和样式
                    for script in content_elem(['script', 'style']):
                        script.decompose()
                    
                    content = content_elem.get_text().strip()
                    # 过滤过短的内容
                    if len(content) < 50:
                        logger.debug(f"跳过过短内容: {title}")
                        continue
                else:
                    content = '无内容'
                
                post_data['content'] = content
                post_data['summary'] = self.generate_summary(content)
                
                # 提取日期
                date_selectors = [
                    'time', '.published', '.post-date', '.entry-date',
                    '.date', '[datetime]', '.timestamp'
                ]
                
                date_elem = None
                for selector in date_selectors:
                    date_elem = container.select_one(selector)
                    if date_elem:
                        break
                
                if date_elem:
                    date_text = date_elem.get('datetime') or date_elem.get_text().strip()
                else:
                    date_text = ''
                
                post_data['publish_date'] = self.extract_date(date_text)
                
                # 提取链接
                link_elem = container.select_one('a[href]')
                if link_elem:
                    post_data['url'] = urljoin(page_url, link_elem['href'])
                else:
                    post_data['url'] = page_url
                
                # 验证数据质量
                if post_data['title'] and len(post_data['content']) >= 50:
                    posts.append(post_data)
                    logger.debug(f"解析文章: {post_data['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"解析文章时出错: {e}")
                continue
        
        return posts
    
    def save_posts_batch(self, posts_batch):
        """批量保存文章到JSON文件"""
        try:
            for post_data in posts_batch:
                if not data_manager.post_exists(post_data['url']):
                    data_manager.add_post(post_data)
                    logger.info(f"保存文章: {post_data['title']}")
                else:
                    logger.info(f"文章已存在，跳过: {post_data['title']}")
            
            data_manager.save_data()
            logger.info(f"批量保存完成，共 {len(posts_batch)} 篇文章")
            
        except Exception as e:
            logger.error(f"保存文章失败: {e}")

    def crawl_single_page(self, url):
        """爬取单个页面"""
        if url in self.crawled_urls or self.posts_count >= self.target_count:
            return [], []
        
        with self.lock:
            self.crawled_urls.add(url)
        
        logger.info(f"正在爬取: {url}")
        
        html_content = self.get_page_content(url)
        if not html_content:
            return [], []
        
        # 解析文章
        posts = self.parse_blog_posts(html_content, url)
        
        # 发现新的URL
        new_urls = set()
        if self.posts_count < self.target_count:
            pagination_urls = self.discover_pagination_urls(html_content, url)
            archive_urls = self.discover_archive_urls(html_content, url)
            new_urls = pagination_urls.union(archive_urls)
            
            # 过滤已爬取的URL
            new_urls = new_urls - self.crawled_urls - self.discovered_urls
            
            with self.lock:
                self.discovered_urls.update(new_urls)
        
        # 添加随机延迟
        time.sleep(self.get_random_delay())
        
        return posts, list(new_urls)
    
    def crawl_all_posts(self):
        """爬取所有文章 - 多线程版本"""
        logger.info(f"开始深度爬取，目标: {self.target_count} 篇文章")
        logger.info(f"起始URL: {self.base_url}")
        
        # 初始化URL队列
        url_queue = [self.base_url]
        all_posts = []
        
        # 第一阶段：发现所有可能的URL
        logger.info("第一阶段：发现URL...")
        initial_html = self.get_page_content(self.base_url)
        if initial_html:
            pagination_urls = self.discover_pagination_urls(initial_html, self.base_url)
            archive_urls = self.discover_archive_urls(initial_html, self.base_url)
            url_queue.extend(list(pagination_urls.union(archive_urls)))
        
        logger.info(f"发现 {len(url_queue)} 个初始URL")
        
        # 第二阶段：并发爬取
        logger.info("第二阶段：并发爬取...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            batch_size = 50  # 批量处理大小
            posts_batch = []
            
            while url_queue and self.posts_count < self.target_count:
                # 提交爬取任务
                current_batch = url_queue[:min(self.max_workers * 2, len(url_queue))]
                url_queue = url_queue[len(current_batch):]
                
                future_to_url = {
                    executor.submit(self.crawl_single_page, url): url 
                    for url in current_batch
                }
                
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        posts, new_urls = future.result()
                        
                        if posts:
                            posts_batch.extend(posts)
                            logger.info(f"从 {url} 获取到 {len(posts)} 篇文章")
                        
                        # 添加新发现的URL到队列
                        if new_urls and self.posts_count < self.target_count:
                            url_queue.extend(new_urls)
                            logger.debug(f"发现 {len(new_urls)} 个新URL")
                        
                        # 批量保存
                        if len(posts_batch) >= batch_size:
                            saved, updated = self.save_posts_batch(posts_batch)
                            all_posts.extend(posts_batch)
                            posts_batch = []
                            
                            logger.info(f"进度: {self.posts_count}/{self.target_count} 篇文章")
                            
                            if self.posts_count >= self.target_count:
                                logger.info("已达到目标文章数量！")
                                break
                    
                    except Exception as e:
                        logger.error(f"处理 {url} 时出错: {e}")
                
                # 如果还有剩余的文章需要保存
                if posts_batch:
                    saved, updated = self.save_posts_batch(posts_batch)
                    all_posts.extend(posts_batch)
                    posts_batch = []
                
                # 检查是否需要继续
                if self.posts_count >= self.target_count:
                    break
                
                # 如果URL队列为空但还没达到目标，尝试更深层的发现
                if not url_queue and self.posts_count < self.target_count:
                    logger.info("尝试发现更多URL...")
                    # 可以在这里添加更多URL发现逻辑
                    break
        
        # 最终统计
        total_crawled = len(self.crawled_urls)
        total_failed = len(self.failed_urls)
        
        logger.info(f"爬取完成！")
        logger.info(f"总共爬取文章: {self.posts_count} 篇")
        logger.info(f"爬取页面: {total_crawled} 个")
        logger.info(f"失败页面: {total_failed} 个")
        
        if self.failed_urls:
            logger.info(f"失败的URL: {list(self.failed_urls)[:10]}...")  # 只显示前10个
        
        return all_posts

def main():
    """主函数"""
    base_url = "https://example-blog.com"  # 替换为实际的博客URL
    
    crawler = EnhancedBlogCrawler(
        base_url=base_url,
        target_count=1000,
        max_workers=5
    )
    
    try:
        crawler.crawl_all_posts()
        logger.info("爬取任务完成！")
    except KeyboardInterrupt:
        logger.info("爬取被用户中断")
    except Exception as e:
        logger.error(f"爬取过程中出现错误: {e}")

if __name__ == '__main__':
    main()