from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re

db = SQLAlchemy()

class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)  # 文章摘要
    url = db.Column(db.String(1000))
    publish_date = db.Column(db.Date, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<BlogPost {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'url': self.url,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def search(query, page=1, per_page=10):
        """全文搜索"""
        search_query = f"%{query}%"
        return BlogPost.query.filter(
            db.or_(
                BlogPost.title.like(search_query),
                BlogPost.content.like(search_query),
                BlogPost.summary.like(search_query)
            )
        ).order_by(BlogPost.publish_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_by_date_range(start_date=None, end_date=None, page=1, per_page=10):
        """按日期范围查询"""
        query = BlogPost.query
        
        if start_date:
            query = query.filter(BlogPost.publish_date >= start_date)
        if end_date:
            query = query.filter(BlogPost.publish_date <= end_date)
            
        return query.order_by(BlogPost.publish_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_date_groups():
        """获取按年月分组的文章统计"""
        from sqlalchemy import func, extract
        
        result = db.session.query(
            extract('year', BlogPost.publish_date).label('year'),
            extract('month', BlogPost.publish_date).label('month'),
            func.count(BlogPost.id).label('count')
        ).filter(
            BlogPost.publish_date.isnot(None)
        ).group_by(
            extract('year', BlogPost.publish_date),
            extract('month', BlogPost.publish_date)
        ).order_by(
            extract('year', BlogPost.publish_date).desc(),
            extract('month', BlogPost.publish_date).desc()
        ).all()
        
        return result