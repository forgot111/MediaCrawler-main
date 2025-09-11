#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动抖音评论图片显示功能

此脚本会：
1. 设置配置以启用Web界面
2. 启动Web服务器显示评论
3. 支持查看评论中的图片

使用方法：
1. 先运行抖音爬虫抓取带图片的评论数据
2. 运行此脚本启动Web界面
3. 访问 http://localhost:8082 查看效果
"""

import asyncio
import sys
import os

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(__file__))

# 导入配置
import config

async def start_web_with_image_support():
    """启动支持图片显示的Web界面"""
    
    print("🎨 抖音评论图片显示功能")
    print("=" * 50)
    
    # 设置配置
    config.SAVE_DATA_OPTION = "web"
    config.PLATFORM = "dy"
    
    print("📋 当前配置:")
    print(f"   平台: {config.PLATFORM}")
    print(f"   数据保存方式: {config.SAVE_DATA_OPTION}")
    print(f"   抓取类型: {config.CRAWLER_TYPE}")
    print(f"   目标视频ID: {config.DY_SPECIFIED_ID_LIST}")
    
    print("\n🚀 启动Web服务器...")
    
    # 动态导入Web存储实现
    from store.douyin.douyin_web_store import DouyinWebStoreImplement
    
    # 创建Web存储实例
    web_store = DouyinWebStoreImplement()
    
    # 检查是否有现有数据
    data_file = os.path.join(web_store.web_path, 'data.json')
    if os.path.exists(data_file):
        print("✅ 发现现有评论数据")
        
        # 读取现有数据检查图片
        import json
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                comments = data.get('comments', [])
                image_comments = [c for c in comments if c.get('评论图片', '').strip()]
                
                print(f"📊 数据统计:")
                print(f"   总评论数: {len(comments)}")
                print(f"   带图片评论: {len(image_comments)}")
                
                if image_comments:
                    print("📸 发现带图片的评论:")
                    for i, comment in enumerate(image_comments[:3]):  # 显示前3条
                        images = comment.get('评论图片', '').split(',')
                        print(f"   {i+1}. {comment.get('用户昵称', 'Unknown')}: {len(images)}张图片")
                    if len(image_comments) > 3:
                        print(f"   ... 还有{len(image_comments) - 3}条带图片的评论")
                        
        except Exception as e:
            print(f"⚠️  读取数据文件失败: {e}")
    else:
        print("⚠️  未发现现有数据")
        print("   请先运行抖音爬虫抓取评论数据:")
        print("   uv run main.py --platform dy --lt qrcode --type detail")
    
    print("\n🌐 Web服务器信息:")
    print("   访问地址: http://localhost:8082")
    print("   备用地址: http://localhost:8083")
    
    print("\n📸 图片功能测试指南:")
    print("   1. 在评论列表中查找带图片的评论")
    print("   2. 点击图片缩略图查看大图")
    print("   3. 在二级评论对话中查看图片")
    print("   4. 使用ESC键或点击外部关闭图片")
    
    print("\n💡 功能亮点:")
    print("   ✨ 三列网格布局显示评论")
    print("   📱 响应式设计支持移动端")
    print("   🖼️  图片缩略图和大图查看")
    print("   💬 二级评论对话展示")
    print("   🔍 用户昵称搜索功能")
    print("   📄 分页浏览评论")
    
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 保持服务器运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 正在停止服务器...")
        
if __name__ == "__main__":
    try:
        asyncio.run(start_web_with_image_support())
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n🔧 解决方法:")
        print("   1. 确保已安装所有依赖: uv sync")
        print("   2. 确保端口8082/8083未被占用")
        print("   3. 检查是否有足够的权限")