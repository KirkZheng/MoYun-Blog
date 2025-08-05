from flask import Flask, render_template, request
from data_manager import data_manager

app = Flask(__name__)

@app.route('/')
def index():
    """主页"""
    result = data_manager.get_all_posts(page=1, per_page=12)
    return render_template('index.html', posts=result)

@app.route('/search')
def search():
    """搜索页面"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    if query:
        result = data_manager.search_posts(query, page=page, per_page=12)
    else:
        result = data_manager.get_all_posts(page=page, per_page=12)
    
    return render_template('search.html', posts=result, query=query)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    """文章详情页"""
    post = data_manager.get_post_by_id(post_id)
    if not post:
        return "文章不存在", 404
    return render_template('post_detail.html', post=post)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)