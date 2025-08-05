from flask import Flask, render_template, request, jsonify
from data_manager import data_manager
from datetime import datetime, date
import calendar

def create_app():
    app = Flask(__name__)
    return app

app = create_app()

@app.route('/')
def index():
    """主页"""
    page = 1
    per_page = 12
    
    result = data_manager.get_all_posts(page=page, per_page=per_page)
    
    return render_template('index.html', posts=result)

@app.route('/search')
def search():
    """搜索页面"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    if query:
        result = data_manager.search_posts(query, page=page, per_page=per_page)
    else:
        result = data_manager.get_all_posts(page=page, per_page=per_page)
    
    return render_template('search.html', posts=result, query=query)

@app.route('/archive')
def archive():
    """归档页面"""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    if year or month:
        result = data_manager.get_posts_by_date(year=year, month=month, page=page, per_page=per_page)
        archive_title = f"{year}年{month}月" if year and month else f"{year}年" if year else f"{month}月"
    else:
        result = data_manager.get_all_posts(page=page, per_page=per_page)
        archive_title = "所有文章"
    
    # 获取日期分组
    date_groups = data_manager.get_date_groups()
    
    return render_template('archive.html', 
                         posts=result, 
                         date_groups=date_groups,
                         archive_title=archive_title,
                         current_year=year,
                         current_month=month)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    """文章详情页"""
    post = data_manager.get_post_by_id(post_id)
    if not post:
        return "文章不存在", 404
    
    return render_template('post_detail.html', post=post)

@app.route('/api/posts')
def api_posts():
    """API: 获取文章列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    
    result = data_manager.get_all_posts(page=page, per_page=per_page)
    
    # 为前端优化数据格式
    for post in result['posts']:
        # 确保日期格式一致
        if post.get('publish_date') and hasattr(post['publish_date'], 'strftime'):
            post['publish_date'] = post['publish_date'].strftime('%Y-%m-%d')
        if post.get('created_at') and hasattr(post['created_at'], 'strftime'):
            post['created_at'] = post['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'success': True,
        'data': result
    })

@app.route('/api/search')
def api_search():
    """API: 搜索文章"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    if not query:
        return jsonify({'success': False, 'message': '搜索关键词不能为空'})
    
    result = data_manager.search_posts(query, page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': result,
        'query': query
    })

@app.route('/api/stats')
def api_stats():
    """API: 获取统计信息"""
    stats = data_manager.get_stats()
    return jsonify({
        'success': True,
        'data': stats
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)