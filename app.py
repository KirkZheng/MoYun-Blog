from flask import Flask, render_template, request, jsonify
from data_manager import data_manager

def create_app():
    app = Flask(__name__)
    return app

app = create_app()

@app.route('/')
def index():
    """主页 - 过滤纯英文文章，按热度排序"""
    page = 1
    per_page = 12
    
    # 获取过滤纯英文文章的结果，按热度排序
    result = data_manager.get_filtered_posts(filter_english=True, page=page, per_page=per_page)
    
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

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    """文章详情页"""
    post = data_manager.get_post_by_id(post_id)
    if not post:
        return "文章不存在", 404
    
    return render_template('post_detail.html', post=post)

@app.route('/api/posts')
def api_posts():
    """API: 获取文章列表（用于无限滚动）- 过滤纯英文，按热度排序"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    
    result = data_manager.get_filtered_posts(filter_english=True, page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': result
    })

@app.route('/stats')
def stats():
    """统计页面"""
    stats_data = data_manager.get_stats()
    return render_template('stats.html', stats=stats_data)

@app.route('/api/stats')
def api_stats():
    """API: 获取统计数据"""
    stats_data = data_manager.get_stats()
    return jsonify({
        'success': True,
        'data': stats_data
    })

@app.route('/api/stats/language')
def api_language_stats():
    """API: 获取语言分布统计"""
    language_data = data_manager.get_language_distribution()
    return jsonify({
        'success': True,
        'data': language_data
    })

@app.route('/api/stats/trend')
def api_trend_stats():
    """API: 获取月度趋势统计"""
    months = request.args.get('months', 12, type=int)
    trend_data = data_manager.get_monthly_trend(months)
    return jsonify({
        'success': True,
        'data': trend_data
    })

@app.route('/api/stats/content')
def api_content_stats():
    """API: 获取内容分析统计"""
    content_data = data_manager.get_content_analysis()
    return jsonify({
        'success': True,
        'data': content_data
    })

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)