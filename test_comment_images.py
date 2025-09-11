#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评论图片显示功能测试

用法:
1. 确保抖音爬虫已运行并设置 SAVE_DATA_OPTION = "web" 
2. 运行这个脚本启动Web服务器
3. 访问 http://localhost:8082 查看效果
"""

import asyncio
import sys
import os

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(__file__))

from store.douyin.douyin_web_store import DouyinWebStoreImplement

async def test_web_with_images():
    """测试Web界面图片显示功能"""
    print("🚀 启动评论图片显示功能测试...")
    
    # 创建Web存储实例
    web_store = DouyinWebStoreImplement()
    
    # 模拟一些带图片的评论数据
    test_comments = [
        {
            '评论时间': '2024-01-15 10:30:00',
            '用户昵称': '小佳和万兴_zz',
            '评论内容': '这个视频很有意思！',
            '点赞数': 25,
            '被回复人昵称': '',
            '作者已赞': '否',
            'ip归属': '天津',
            '评论图片': 'https://p3-pc.douyinpic.com/img/tos-cn-p-0000/example1.jpg,https://p3-pc.douyinpic.com/img/tos-cn-p-0000/example2.jpg',
            '评论ID': 'test001',
            '视频ID': '7548310409170783498',
            '用户ID': 'user001',
        },
        {
            '评论时间': '2024-01-15 10:25:00',
            '用户昵称': '摄影爱好者',
            '评论内容': '很棒的拍摄角度',
            '点赞数': 15,
            '被回复人昵称': '小佳和万兴_zz',
            '作者已赞': '是',
            'ip归属': '北京',
            '评论图片': 'https://p3-pc.douyinpic.com/img/tos-cn-p-0000/example3.jpg',
            '评论ID': 'test002',
            '视频ID': '7548310409170783498',
            '用户ID': 'user002',
        },
        {
            '评论时间': '2024-01-15 10:20:00',
            '用户昵称': '普通用户',
            '评论内容': '没有图片的普通评论，但是内容比较长，会被截断显示，需要点击展开按钮才能看到完整内容。这是一个测试长文本的例子。',
            '点赞数': 8,
            '被回复人昵称': '',
            '作者已赞': '否',
            'ip归属': '上海',
            '评论图片': '',
            '评论ID': 'test003',
            '视频ID': '7548310409170783498',
            '用户ID': 'user003',
        }
    ]
    
    # 批量导入测试评论
    await web_store.bulk_import_comments(test_comments)
    
    print("✅ 测试数据已导入")
    print("📊 数据统计:")
    print(f"   - 总评论数: {len(test_comments)}")
    print(f"   - 带图片评论: {sum(1 for c in test_comments if c['评论图片'])}")
    print(f"   - 二级评论数: {sum(1 for c in test_comments if c['被回复人昵称'])}")
    
    # 启动Web服务器
    print("\n🌐 启动Web服务器...")
    print("📱 访问地址: http://localhost:8082")
    print("📸 功能测试:")
    print("   1. 查看评论列表中的图片缩略图")
    print("   2. 点击图片查看大图")
    print("   3. 点击二级评论查看对话中的图片")
    print("   4. 测试ESC键关闭图片")
    print("\n⚠️  注意: 测试图片URL可能无法加载，这是正常的")
    print("   真实使用时会显示抖音平台的真实图片")
    print("\n按 Ctrl+C 停止服务器")
    
    # 保持服务器运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 停止服务器")

if __name__ == "__main__":
    asyncio.run(test_web_with_images())