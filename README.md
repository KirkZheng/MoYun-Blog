# 增强版博客爬虫和网站展示系统

这是一个功能完整的博客爬虫项目，支持MySQL数据库缓存、按日期分类和全文搜索功能。

## 🚀 新增功能

- 🗄️ **MySQL数据库缓存**：使用MySQL存储爬取的数据，支持增量更新
- 📅 **按日期分类**：自动按年月归档文章，方便浏览
- 🔍 **全文搜索**：支持标题和内容的关键词搜索
- 📄 **分页浏览**：大量文章的分页显示
- 📱 **响应式设计**：完美支持移动端访问
- 🔗 **RESTful API**：提供完整的API接口

## 📋 系统要求

- Python 3.7+
- MySQL 5.7+ 或 MariaDB 10.2+

## ⚙️ 配置说明

### 数据库配置

在 `config.py` 中配置MySQL连接信息：

```python
MYSQL_HOST = 'localhost'      # MySQL服务器地址
MYSQL_PORT = 3306             # MySQL端口
MYSQL_USER = 'root'           # 用户名
MYSQL_PASSWORD = ''           # 密码
MYSQL_DATABASE = 'blog_crawler'  # 数据库名
```

或使用环境变量：

```bash
set MYSQL_HOST=localhost
set MYSQL_USER=root
set MYSQL_PASSWORD=your_password
set MYSQL_DATABASE=blog_crawler
```

## 🚀 快速开始

### 方法一：一键运行
```bash
python run.py
```

### 方法二：分步运行

1. **安装依赖**：
```bash
pip install -r requirements.txt
```

2. **配置数据库**：
   - 确保MySQL服务已启动
   - 修改 `config.py` 中的数据库配置

3. **运行爬虫**：
```bash
python crawler.py
```

4. **启动网站**：
```bash
python app.py
```

5. **访问网站**：
   - 首页：http://localhost:5000
   - 搜索：http://localhost:5000/search
   - 归档：http://localhost:5000/archive

## 📁 项目结构