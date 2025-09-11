#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试作者已赞功能

这个脚本用于测试新增的"作者已赞"标签页功能
"""

import asyncio
import sys
import os

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(__file__))

from store.douyin.douyin_web_store import DouyinWebStoreImplement

async def test_author_liked_feature():
    """测试作者已赞功能"""
    print("⭐ 测试作者已赞功能...")
    
    # 创建Web存储实例
    web_store = DouyinWebStoreImplement()
    
    # 模拟包含作者已赞评论的测试数据
    test_comments = [
        {
            '评论时间': '2024-01-15 10:30:00',
            '用户昵称': '东明朗春',
            '评论内容': '异安朋友们多睡会儿呀',
            '点赞数': 3,
            '被回复人昵称': '',
            '被回复人原先的内容': '',
            '作者已赞': '是',  # 作者已赞
            'ip归属': '宁夏',
            '评论图片': 'https://p3-pc.douyinpic.com/img/tos-cn-p-0000/example1.jpg',
            '评论ID': 'comment_001',
            '视频ID': '7548310409170783498',
            '用户ID': 'user001',
            '父评论ID': '0',
        },
        {
            '评论时间': '2024-01-15 10:25:00', 
            '用户昵称': '佳佳子_zz',
            '评论内容': '回复 @东明朗春: 哈哈',
            '点赞数': 62,
            '被回复人昵称': '东明朗春',
            '被回复人原先的内容': '异安朋友们多睡会儿呀',
            '作者已赞': '否',  # 作者未赞
            'ip归属': '上海',
            '评论图片': '',
            '评论ID': 'comment_002',
            '视频ID': '7548310409170783498', 
            '用户ID': 'user002',
            '父评论ID': 'comment_001',
        },
        {
            '评论时间': '2024-01-15 09:30:00',
            '用户昵称': '小红书用户',
            '评论内容': '这个视频太棒了！真的很有创意，学到了很多东西。希望能看到更多这样的内容。',
            '点赞数': 15,
            '被回复人昵称': '',
            '被回复人原先的内容': '',
            '作者已赞': '是',  # 作者已赞
            'ip归属': '北京',
            '评论图片': 'https://p3-pc.douyinpic.com/img/tos-cn-p-0000/example2.jpg',
            '评论ID': 'comment_003',
            '视频ID': '7548310409170783498',
            '用户ID': 'user003',
            '父评论ID': '0',
        },
        {
            '评论时间': '2024-01-15 09:20:00',
            '用户昵称': '摄影爱好者',
            '评论内容': '镜头运用得很好',
            '点赞数': 8,
            '被回复人昵称': '',
            '被回复人原先的内容': '',
            '作者已赞': '否',  # 作者未赞
            'ip归属': '广州',
            '评论图片': '',
            '评论ID': 'comment_004',
            '视频ID': '7548310409170783498',
            '用户ID': 'user004',
            '父评论ID': '0',
        },
        {
            '评论时间': '2024-01-15 09:10:00',
            '用户昵称': '音乐发烧友',
            '评论内容': '背景音乐选得很棒，和视频内容完美契合！',
            '点赞数': 25,
            '被回复人昵称': '',
            '被回复人原先的内容': '',
            '作者已赞': '是',  # 作者已赞
            'ip归属': '深圳',
            '评论图片': '',
            '评论ID': 'comment_005',
            '视频ID': '7548310409170783498',
            '用户ID': 'user005',
            '父评论ID': '0',
        },
        {
            '评论时间': '2024-01-15 09:00:00',
            '用户昵称': '普通观众',
            '评论内容': '还不错',
            '点赞数': 2,
            '被回复人昵称': '',
            '被回复人原先的内容': '',
            '作者已赞': '否',  # 作者未赞
            'ip归属': '杭州',
            '评论图片': '',
            '评论ID': 'comment_006',
            '视频ID': '7548310409170783498',
            '用户ID': 'user006',
            '父评论ID': '0',
        }
    ]
    
    # 批量导入测试评论
    await web_store.bulk_import_comments(test_comments)
    
    print("✅ 测试数据已导入")
    print("📊 数据统计:")
    
    # 统计数据
    total_comments = len(test_comments)
    author_liked_comments = [c for c in test_comments if c['作者已赞'] == '是']
    author_not_liked_comments = [c for c in test_comments if c['作者已赞'] == '否']
    
    print(f"   总评论数: {total_comments}")
    print(f"   作者已赞评论: {len(author_liked_comments)}")
    print(f"   作者未赞评论: {len(author_not_liked_comments)}")
    
    print("\n⭐ 作者已赞的评论:")
    for i, comment in enumerate(author_liked_comments, 1):
        user = comment['用户昵称']
        content = comment['评论内容'][:30] + "..." if len(comment['评论内容']) > 30 else comment['评论内容']
        likes = comment['点赞数']
        location = comment['ip归属']
        time = comment['评论时间'][5:16]
        print(f"   {i}. {user} ({location}) - {likes}赞 - {time}")
        print(f"      {content}")
    
    print("\n🌐 Web服务器信息:")
    print("   访问地址: http://localhost:8082")
    print("\n📝 测试指南:")
    print("   1. 点击 '作者已赞' 标签页")
    print(f"   2. 应该看到 {len(author_liked_comments)} 条作者已赞的评论")
    print("   3. 评论按时间排序（最新的在前）")
    print("   4. 采用三列网格布局显示")
    print("   5. 支持分页浏览（每页12条）")
    print("   6. 每条评论都应该显示'作者已赞'标识")
    
    print("\n💡 功能特点:")
    print("   ✨ 独立的标签页展示作者已赞评论")
    print("   📱 与最新评论页相同的样式和布局")
    print("   🖼️  支持图片显示和大图查看")
    print("   💬 支持二级评论对话查看")
    print("   📄 支持分页浏览")
    print("   ⏰ 按时间排序显示")
    
    print("\n按 Ctrl+C 停止服务器")
    
    # 保持服务器运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 停止服务器")

if __name__ == "__main__":
    asyncio.run(test_author_liked_feature())