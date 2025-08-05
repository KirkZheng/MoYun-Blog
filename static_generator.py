import os
import json
from jinja2 import Environment, FileSystemLoader
from data_manager import data_manager
import shutil
from urllib.parse import quote

class StaticSiteGenerator:
    def __init__(self, output_dir='docs'):
        self.output_dir = output_dir
        self.template_env = Environment(loader=FileSystemLoader('templates'))
        
    def ensure_output_dir(self):
        """确保输出目录存在"""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 创建必要的子目录
        os.makedirs(os.path.join(self.output_dir, 'post'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'static'), exist_ok=True)
        
    def copy_static_files(self):
        """复制静态文件"""
        # 如果有static目录，复制它
        if os.path.exists('static'):
            shutil.copytree('static', os.path.join(self.output_dir, 'static'), dirs_exist_ok=True)
            
    def generate_index(self):
        """生成首页"""
        template = self.template_env.get_template('index.html')
        
        # 获取所有文章（用于首页显示）
        result = data_manager.get_all_posts(page=1, per_page=12)
        
        html = template.render(posts=result)
        
        with open(os.path.join(self.output_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
            
    def generate_search_page(self):
        """生成搜索页面"""
        template = self.template_env.get_template('search.html')
        
        # 空的搜索页面
        result = {'posts': [], 'total': 0, 'page': 1, 'per_page': 12, 'has_next': False}
        
        html = template.render(posts=result, query='')
        
        with open(os.path.join(self.output_dir, 'search.html'), 'w', encoding='utf-8') as f:
            f.write(html)
            
    def generate_post_pages(self):
        """生成所有文章详情页"""
        template = self.template_env.get_template('post_detail.html')
        
        # 获取所有文章
        all_posts = data_manager.get_all_posts(page=1, per_page=10000)  # 获取所有文章
        
        for post in all_posts['posts']:
            html = template.render(post=post)
            
            post_file = os.path.join(self.output_dir, 'post', f"{post['id']}.html")
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(html)
                
    def generate_api_data(self):
        """生成API数据文件"""
        # 创建API目录
        api_dir = os.path.join(self.output_dir, 'api')
        os.makedirs(api_dir, exist_ok=True)
        
        # 生成文章列表API数据
        posts_dir = os.path.join(api_dir, 'posts')
        os.makedirs(posts_dir, exist_ok=True)
        
        # 生成分页数据
        page = 1
        while True:
            result = data_manager.get_all_posts(page=page, per_page=12)
            
            api_data = {
                'success': True,
                'data': result
            }
            
            with open(os.path.join(posts_dir, f'page_{page}.json'), 'w', encoding='utf-8') as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)
                
            if not result['has_next']:
                break
            page += 1
            
        # 生成搜索API数据（预生成常见搜索词）
        search_dir = os.path.join(api_dir, 'search')
        os.makedirs(search_dir, exist_ok=True)
        
        # 获取所有文章用于搜索
        all_posts = data_manager.get_all_posts(page=1, per_page=10000)
        
        # 生成完整文章数据用于前端搜索
        search_data = {
            'success': True,
            'posts': all_posts['posts']
        }
        
        with open(os.path.join(search_dir, 'all.json'), 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)
            
    def update_templates_for_static(self):
        """更新模板以适应静态网站"""
        # 读取并修改index.html模板
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 修改API调用为静态文件
        content = content.replace(
            "fetch(`/api/posts?page=${page}&per_page=${perPage}`)",
            "fetch(`./api/posts/page_${page}.json`)"
        )
        
        # 修改链接为相对路径
        content = content.replace('href="/post/', 'href="./post/')
        content = content.replace('href="/search', 'href="./search.html')
        
        with open('templates/index_static.html', 'w', encoding='utf-8') as f:
            f.write(content)
            
        # 修改base.html模板
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            base_content = f.read()
            
        # 修改导航链接
        base_content = base_content.replace('href="/"', 'href="./index.html"')
        base_content = base_content.replace('href="/search"', 'href="./search.html"')
        
        with open('templates/base_static.html', 'w', encoding='utf-8') as f:
            f.write(base_content)
            
    def generate_site(self):
        """生成完整的静态网站"""
        print("开始生成静态网站...")
        
        # 准备输出目录
        self.ensure_output_dir()
        
        # 更新模板
        self.update_templates_for_static()
        
        # 临时切换模板
        original_loader = self.template_env.loader
        
        try:
            # 复制静态文件
            self.copy_static_files()
            
            # 生成页面
            self.generate_index()
            self.generate_search_page()
            self.generate_post_pages()
            
            # 生成API数据
            self.generate_api_data()
            
            print(f"静态网站已生成到 {self.output_dir} 目录")
            
        finally:
            # 恢复原始模板加载器
            self.template_env.loader = original_loader
            
            # 清理临时模板文件
            if os.path.exists('templates/index_static.html'):
                os.remove('templates/index_static.html')
            if os.path.exists('templates/base_static.html'):
                os.remove('templates/base_static.html')

if __name__ == '__main__':
    generator = StaticSiteGenerator()
    generator.generate_site()