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
import json
import os
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

class FastBlogCrawler:
    def __init__(self, base_url, max_workers=10):
        self.base_url = base_url
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 缓存文件
        self.cache_file = 'crawler_cache.json'
        
        # 爬取状态
        self.crawled_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.posts_count = 0
        self.lock = threading.Lock()
        
        # 加载缓存
        self.load_cache()
        
        # 用户代理轮换
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
    
    def load_cache(self):
        """加载爬取缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.crawled_urls = set(cache_data.get('crawled_urls', []))
                    self.failed_urls = set(cache_data.get('failed_urls', []))
                    logger.info(f"加载缓存: 已爬取URL {len(self.crawled_urls)} 个，失败URL {len(self.failed_urls)} 个")
            
            # 从数据管理器加载已存在的文章URL
            existing_urls = set()
            for post in data_manager.posts:
                if post.get('url'):
                    existing_urls.add(post['url'])
            
            self.crawled_urls.update(existing_urls)
            logger.info(f"从数据库加载已存在文章URL: {len(existing_urls)} 个")
            
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            self.crawled_urls = set()
            self.failed_urls = set()
    
    def save_cache(self):
        """保存爬取缓存"""
        try:
            cache_data = {
                'crawled_urls': list(self.crawled_urls),
                'failed_urls': list(self.failed_urls),
                'last_update': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def get_random_delay(self, min_delay=0.5, max_delay=1.5):
        """获取随机延迟时间"""
        return random.uniform(min_delay, max_delay)
    
    def rotate_user_agent(self):
        """轮换用户代理"""
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    def get_page_content(self, url, retries=3):
        """获取页面内容"""
        for attempt in range(retries):
            try:
                self.rotate_user_agent()
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"获取页面失败 (尝试 {attempt + 1}/{retries}): {url} - {e}")
                if attempt < retries - 1:
                    time.sleep(self.get_random_delay(1, 3))
                else:
                    logger.error(f"最终获取失败: {url}")
                    return None
        return None
    
    def extract_date(self, date_text):
        """提取日期"""
        if not date_text:
            return None
        
        # 清理日期文本
        date_text = re.sub(r'[^\d\-/年月日]', '', date_text)
        
        # 尝试多种日期格式
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if len(groups[0]) == 4:  # 年份在前
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # 年份在后
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                        return date(year, month, day)
                except ValueError:
                    continue
        
        return None
    
    def generate_summary(self, content, max_length=200):
        """生成文章摘要"""
        if not content:
            return ""
        
        # 移除HTML标签
        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        if len(clean_content) <= max_length:
            return clean_content
        
        # 尝试在句号处截断
        sentences = re.split(r'[。！？.!?]', clean_content)
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + "。"
            else:
                break
        
        if not summary:
            summary = clean_content[:max_length] + "..."
        
        return summary.strip()
    
    def discover_pagination_urls(self, html_content, base_url):
        """发现分页URL"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = set()
        
        # 查找分页链接
        pagination_selectors = [
            'a[href*="max-results"]',
            'a[href*="start-index"]',
            '.blog-pager a',
            '.pager a',
            'a:contains("下一页")',
            'a:contains("Next")',
            'a:contains("更多")',
            'a:contains("More")'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.base_url in full_url:
                        urls.add(full_url)
        
        return urls
    
    def discover_archive_urls(self, html_content, base_url):
        """发现归档URL"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = set()
        
        # 查找归档链接
        archive_selectors = [
            'a[href*="/search/label/"]',
            'a[href*="archive"]',
            '.archive-link a',
            '.label-link a',
            'a[href*="/p/"]'
        ]
        
        for selector in archive_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.base_url in full_url:
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
            'article',
            '.entry',
            '.post-outer',
            '[class*="post"]'
        ]
        
        post_elements = []
        for selector in post_selectors:
            elements = soup.select(selector)
            if elements:
                post_elements = elements
                break
        
        for post_elem in post_elements:
            try:
                # 提取标题
                title_elem = post_elem.select_one('h1, h2, h3, .post-title, .entry-title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else "无标题"
                
                # 提取链接
                link_elem = post_elem.select_one('a[href]')
                if not link_elem:
                    link_elem = title_elem.select_one('a[href]') if title_elem else None
                
                if not link_elem:
                    continue
                
                post_url = urljoin(page_url, link_elem.get('href'))
                
                # 检查是否已爬取过
                if post_url in self.crawled_urls:
                    continue
                
                # 提取内容
                content_elem = post_elem.select_one('.post-body, .entry-content, .content, [class*="content"]')
                content = content_elem.get_text(strip=True) if content_elem else ""
                
                # 提取日期
                date_elem = post_elem.select_one('.published, .post-timestamp, .date, [class*="date"], time')
                publish_date = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True) or date_elem.get('datetime', '')
                    publish_date = self.extract_date(date_text)
                
                # 生成摘要
                summary = self.generate_summary(content)
                
                post_data = {
                    'title': title,
                    'url': post_url,
                    'content': content,
                    'summary': summary,
                    'publish_date': publish_date,
                    'source_page': page_url,
                    'crawl_time': datetime.now().isoformat()
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
        
        # 过滤已存在的文章
        new_posts = []
        for post in posts_batch:
            if not data_manager.post_exists(post.get('url')):
                new_posts.append(post)
        
        if not new_posts:
            return 0
        
        added_count = data_manager.add_posts_batch(new_posts)
        
        if added_count > 0:
            data_manager.save_data()
            logger.info(f"批量保存了 {added_count} 篇新文章")
            
            # 更新已爬取URL缓存
            with self.lock:
                for post in new_posts:
                    self.crawled_urls.add(post['url'])
            
            # 保存缓存
            self.save_cache()
        
        return added_count
    
    def crawl_single_page(self, url):
        """爬取单个页面"""
        with self.lock:
            if url in self.crawled_urls:
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
            # 只添加未爬取过的URL
            new_urls = (new_pagination_urls | new_archive_urls) - self.crawled_urls
            self.discovered_urls.update(new_urls)
            self.posts_count += len(posts)
        
        # 随机延迟
        time.sleep(self.get_random_delay())
        
        return posts
    
    def crawl_all_posts(self):
        """爬取所有文章 - 无数量限制，直到爬取完成"""
        logger.info(f"开始全量爬取，并发数: {self.max_workers}")
        logger.info(f"已缓存URL数量: {len(self.crawled_urls)}")
        
        # 初始URL
        initial_urls = {
            self.base_url,
            f"{self.base_url}/search?max-results=50",
            f"{self.base_url}/search?updated-max=2024-12-31T23:59:59%2B08:00&max-results=50"
        }
        
        # 过滤已爬取的URL
        new_initial_urls = initial_urls - self.crawled_urls
        self.discovered_urls.update(new_initial_urls)
        
        all_posts = []
        consecutive_empty_rounds = 0
        max_empty_rounds = 3  # 连续3轮没有新文章就停止
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while self.discovered_urls and consecutive_empty_rounds < max_empty_rounds:
                # 获取待爬取的URL
                urls_to_crawl = list(self.discovered_urls - self.crawled_urls)[:self.max_workers * 2]
                
                if not urls_to_crawl:
                    logger.info("没有更多URL可爬取")
                    break
                
                logger.info(f"本轮爬取URL数量: {len(urls_to_crawl)}")
                
                # 提交爬取任务
                future_to_url = {executor.submit(self.crawl_single_page, url): url for url in urls_to_crawl}
                
                batch_posts = []
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        posts = future.result()
                        batch_posts.extend(posts)
                        all_posts.extend(posts)
                        
                    except Exception as e:
                        logger.error(f"爬取失败 {url}: {e}")
                        with self.lock:
                            self.failed_urls.add(url)
                
                # 批量保存
                if batch_posts:
                    saved_count = self.save_posts_batch(batch_posts)
                    logger.info(f"本轮发现 {len(batch_posts)} 篇文章，保存 {saved_count} 篇新文章，总计: {self.posts_count}")
                    consecutive_empty_rounds = 0
                else:
                    consecutive_empty_rounds += 1
                    logger.info(f"本轮未发现新文章 (连续 {consecutive_empty_rounds}/{max_empty_rounds} 轮)")
                
                # 移除已处理的URL
                with self.lock:
                    self.discovered_urls -= set(urls_to_crawl)
        
        # 最终统计
        logger.info(f"爬取完成！")
        logger.info(f"本次新增文章数: {len(all_posts)}")
        logger.info(f"总爬取URL: {len(self.crawled_urls)}")
        logger.info(f"失败URL: {len(self.failed_urls)}")
        
        # 保存最终缓存
        self.save_cache()
        
        return all_posts

def main():
    """主函数"""
    base_url = 'https://hwv430.blogspot.com'
    max_workers = 10
    
    crawler = FastBlogCrawler(base_url, max_workers)
    
    start_time = time.time()
    posts = crawler.crawl_all_posts()
    end_time = time.time()
    
    logger.info(f"爬取耗时: {end_time - start_time:.2f} 秒")
    if posts:
        logger.info(f"平均速度: {len(posts) / (end_time - start_time):.2f} 篇/秒")
    
    # 显示统计信息
    stats = data_manager.get_stats() if hasattr(data_manager, 'get_stats') else {}
    logger.info(f"数据库统计: {stats}")

if __name__ == '__main__':
    main()