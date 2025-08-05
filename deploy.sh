#!/bin/bash

# 部署脚本
echo "开始部署MoYun Blog到GitHub Pages..."

# 运行爬虫更新数据
echo "更新博客数据..."
python crawler.py

# 生成静态网站
echo "生成静态网站..."
python static_generator.py

# 提交到Git
echo "提交更改..."
git add .
git commit -m "Update blog content and regenerate static site"
git push origin main

echo "部署完成！"