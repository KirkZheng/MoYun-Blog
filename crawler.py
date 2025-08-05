import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, date
import re
from urllib.parse import urljoin, urlparse, parse_qs
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Set, Dict
import random
from data_manager import data_manager

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

class BlogCrawler:
    def __init__(self, base_url, target_count=1000, max_workers=10):
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
    
    def get_random_delay(self, min_delay=0.5, max_delay=1.5):
        """获取随机延迟时间（减少延迟提升速度）"""
        return random.uniform(min_delay, max_delay)
    
    def rotate_user_agent(self):
        """轮换用户代理"""
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    def get_page_content(self, url, retries=3):
        """获取页面内容"""
        for attempt in range(retries):
            try:
                self.rotate_user_agent()
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"获取页面失败 (尝试 {attempt + 1}/{retries}): {url} - {e}")
                if attempt < retries - 1:
                    time.sleep(self.get_random_delay(1, 3))
                else:
                    logger.error(f"最终获取失败: {url}")
                    return None
    
    def extract_date(self, date_text):
        """提取日期"""
        if not date_text:
            return None
        
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, str(date_text))
            if match:
                try:
                    if '/' in pattern:
                        month, day, year = match.groups()
                        return date(int(year), int(month), int(day))
                    elif '-' in pattern:
                        year, month, day = match.groups()
                        return date(int(year), int(month), int(day))
                    elif '.' in pattern:
                        day, month, year = match.groups()
                        return date(int(year), int(month), int(day))
                except ValueError:
                    continue
        return None
    
    def generate_summary(self, content, max_length=200):
        """生成文章摘要"""
        if not content:
            return ""
        
        # 移除HTML标签
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 清理文本
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 截取摘要
        if len(text) <= max_length:
            return text
        
        # 在句号处截断
        sentences = text[:max_length].split('。')
        if len(sentences) > 1:
            return '。'.join(sentences[:-1]) + '。'
        
        return text[:max_length] + '...'
    
    def discover_pagination_urls(self, html_content, base_url):
        """发现分页URL"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = set()
        
        # Blogspot分页链接
        pagination_selectors = [
            'a[href*="max-results"]',
            'a[href*="start="]',
            '.blog-pager a',
            '.pagination a',
            'a[href*="page"]'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
        
        return urls
    
    def discover_archive_urls(self, html_content, base_url):
        """发现归档URL"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = set()
        
        # 归档链接选择器
        archive_selectors = [
            'a[href*="archive"]',
            '.archive-link a',
            '.sidebar a[href*="search"]',
            'a[href*="label"]'
        ]
        
        for selector in archive_selectors:
            links = soup.select(selector)
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
        
        # 多种文章选择器
        post_selectors = [
            '.post',
            '.blog-post',
            '.entry',
            'article',
            '.post-outer',
            '.hentry'
        ]
        
        post_elements = []
        for selector in post_selectors:
            elements = soup.select(selector)
            if elements:
                post_elements = elements
                break
        
        for post_element in post_elements:
            try:
                # 提取标题
                title_selectors = [
                    '.post-title a',
                    '.entry-title a',
                    'h3 a',
                    'h2 a',
                    'h1 a',
                    '.post-title',
                    '.entry-title'
                ]
                
                title = None
                post_url = None
                
                for title_selector in title_selectors:
                    title_element = post_element.select_one(title_selector)
                    if title_element:
                        title = title_element.get_text().strip()
                        if title_element.name == 'a':
                            post_url = title_element.get('href')
                        break
                
                if not title:
                    continue
                
                # 如果没有找到链接，尝试其他方式
                if not post_url:
                    link_selectors = ['a[href*=".html"]', 'a[href*="/20"]']
                    for link_selector in link_selectors:
                        link_element = post_element.select_one(link_selector)
                        if link_element:
                            post_url = link_element.get('href')
                            break
                
                if post_url:
                    post_url = urljoin(page_url, post_url)
                
                # 提取内容
                content_selectors = [
                    '.post-body',
                    '.entry-content',
                    '.post-content',
                    '.content'
                ]
                
                content = ""
                for content_selector in content_selectors:
                    content_element = post_element.select_one(content_selector)
                    if content_element:
                        content = str(content_element)
                        break
                
                # 提取日期
                date_selectors = [
                    '.published',
                    '.post-timestamp',
                    '.date',
                    '.post-date',
                    'time',
                    '.entry-date'
                ]
                
                publish_date = None
                for date_selector in date_selectors:
                    date_element = post_element.select_one(date_selector)
                    if date_element:
                        date_text = date_element.get_text() or date_element.get('datetime') or date_element.get('title')
                        publish_date = self.extract_date(date_text)
                        if publish_date:
                            break
                
                # 生成摘要
                summary = self.generate_summary(content)
                
                post_data = {
                    'title': title,
                    'url': post_url,
                    'content': content,
                    'summary': summary,
                    'publish_date': publish_date
                }
                
                posts.append(post_data)
                
            except Exception as e:
                logger.warning(f"解析文章失败: {e}")
                continue
        
        return posts
    
    def save_posts_batch(self, posts_batch):
        """批量保存文章到本地缓存"""
        if not posts_batch:
            return 0
        
        added_count = data_manager.add_posts_batch(posts_batch)
        
        if added_count > 0:
            data_manager.save_data()
            logger.info(f"批量保存了 {added_count} 篇新文章")
        
        return added_count
    
    def crawl_single_page(self, url):
        """爬取单个页面"""
        with self.lock:
            if url in self.crawled_urls or self.posts_count >= self.target_count:
                return []
            self.crawled_urls.add(url)
        
        logger.info(f"正在爬取: {url}")
        
        html_content = self.get_page_content(url)
        if not html_content:
            with self.lock:
                self.failed_urls.add(url)
            return []
        
        # 解析文章
        posts = self.parse_blog_posts(html_content, url)
        
        # 发现新的URL
        new_pagination_urls = self.discover_pagination_urls(html_content, url)
        new_archive_urls = self.discover_archive_urls(html_content, url)
        
        with self.lock:
            self.discovered_urls.update(new_pagination_urls)
            self.discovered_urls.update(new_archive_urls)
            self.posts_count += len(posts)
        
        # 随机延迟（减少延迟）
        time.sleep(self.get_random_delay())
        
        return posts
    
    def crawl_all_posts(self):
        """爬取所有文章"""
        logger.info(f"开始爬取，目标: {self.target_count} 篇文章，并发数: {self.max_workers}")
        
        # 初始URL
        initial_urls = {
            self.base_url,
            f"{self.base_url}/search?max-results=50",
            f"{self.base_url}/search?updated-max=2024-12-31T23:59:59%2B08:00&max-results=50"
        }
        
        self.discovered_urls.update(initial_urls)
        all_posts = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while self.discovered_urls and self.posts_count < self.target_count:
                # 获取待爬取的URL
                urls_to_crawl = list(self.discovered_urls - self.crawled_urls)[:self.max_workers * 2]
                
                if not urls_to_crawl:
                    break
                
                # 提交爬取任务
                future_to_url = {executor.submit(self.crawl_single_page, url): url for url in urls_to_crawl}
                
                batch_posts = []
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        posts = future.result()
                        batch_posts.extend(posts)
                        all_posts.extend(posts)
                        
                        logger.info(f"已爬取 {len(posts)} 篇文章，总计: {self.posts_count}/{self.target_count}")
                        
                    except Exception as e:
                        logger.error(f"爬取失败 {url}: {e}")
                        with self.lock:
                            self.failed_urls.add(url)
                
                # 批量保存
                if batch_posts:
                    self.save_posts_batch(batch_posts)
                
                # 检查是否达到目标
                if self.posts_count >= self.target_count:
                    logger.info(f"已达到目标文章数: {self.posts_count}")
                    break
        
        # 最终统计
        logger.info(f"爬取完成！")
        logger.info(f"总文章数: {len(all_posts)}")
        logger.info(f"成功URL: {len(self.crawled_urls)}")
        logger.info(f"失败URL: {len(self.failed_urls)}")
        
        return all_posts

def main():
    """主函数"""
    base_url = 'https://hwv430.blogspot.com'  # 目标博客URL
    target_count = 1000                     # 目标文章数量
    max_workers = 10                          # 并发线程数
    
    crawler = BlogCrawler(base_url, target_count, max_workers)
    
    start_time = time.time()
    posts = crawler.crawl_all_posts()
    end_time = time.time()
    
    logger.info(f"爬取耗时: {end_time - start_time:.2f} 秒")
    logger.info(f"平均速度: {len(posts) / (end_time - start_time):.2f} 篇/秒")
    
    # 显示统计信息
    stats = data_manager.get_stats()
    logger.info(f"数据库统计: {stats}")

if __name__ == '__main__':
    main()