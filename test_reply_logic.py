#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试二级评论逻辑修复

这个脚本用于验证二级评论和一级评论的精确对应关系
"""

import asyncio
import sys
import os

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(__file__))

from store.douyin.douyin_web_store import DouyinWebStoreImplement

async def test_reply_logic():
    """测试修复后的二级评论逻辑"""
    print("🔧 测试二级评论逻辑修复...")
    
    # 创建Web存储实例
    web_store = DouyinWebStoreImplement()
    
    # 模拟真实的评论数据结构
    test_comments = [
        {
            '评论时间': '2024-01-15 10:30:00',
            '用户昵称': '东明朗春',
            '评论内容': '异安朋友们多睡会儿呀',
            '点赞数': 3,
            '被回复人昵称': '',
            '被回复人原先的内容': '',
            '作者已赞': '否',
            'ip归属': '宁夏',
            '评论图片': 'https://p3-pc.douyinpic.com/img/tos-cn-p-0000/example1.jpg',
            '评论ID': 'comment_001',  # 一级评论ID
            '视频ID': '7548310409170783498',
            '用户ID': 'user001',
            '父评论ID': '0',  # 一级评论的父评论ID为0
        },
        {
            '评论时间': '2024-01-15 10:25:00', 
            '用户昵称': '佳佳子_zz',
            '评论内容': '回复 @东明朗春: 哈哈',
            '点赞数': 62,
            '被回复人昵称': '东明朗春',
            '被回复人原先的内容': '异安朋友们多睡会儿呀',
            '作者已赞': '否',
            'ip归属': '上海',
            '评论图片': '',
            '评论ID': 'comment_002',  # 二级评论ID
            '视频ID': '7548310409170783498', 
            '用户ID': 'user002',
            '父评论ID': 'comment_001',  # 指向一级评论的ID
        },
        {
            '评论时间': '2024-01-15 09:30:00',
            '用户昵称': '东明朗春',
            '评论内容': '这是另一条不相关的评论',
            '点赞数': 5,
            '被回复人昵称': '',
            '被回复人原先的内容': '',
            '作者已赞': '否',
            'ip归属': '宁夏',
            '评论图片': '',
            '评论ID': 'comment_003',  # 另一条一级评论
            '视频ID': '7548310409170783498',
            '用户ID': 'user001',
            '父评论ID': '0',
        }
    ]
    
    # 批量导入测试评论
    await web_store.bulk_import_comments(test_comments)
    
    print("✅ 测试数据已导入")
    print("📊 数据验证:")
    
    # 验证数据关系
    for comment in test_comments:
        user = comment['用户昵称']
        content = comment['评论内容'][:20] + "..." if len(comment['评论内容']) > 20 else comment['评论内容']
        parent_id = comment['父评论ID']
        comment_id = comment['评论ID']
        
        if parent_id == '0':
            print(f"   一级评论: {user} - {content} (ID: {comment_id})")
        else:
            # 找到父评论
            parent_comment = next((c for c in test_comments if c['评论ID'] == parent_id), None)
            if parent_comment:
                parent_user = parent_comment['用户昵称']
                parent_content = parent_comment['评论内容'][:15] + "..." if len(parent_comment['评论内容']) > 15 else parent_comment['评论内容']
                print(f"   二级评论: {user} 回复 {parent_user} - {content}")
                print(f"     └─ 对应一级评论: {parent_user} - {parent_content} (ID: {parent_id})")
            else:
                print(f"   ⚠️  二级评论 {user} 的父评论ID {parent_id} 未找到!")
    
    print("\n🌐 Web服务器信息:")
    print("   访问地址: http://localhost:8082")
    print("\n📝 测试指南:")
    print("   1. 点击 '佳佳子_zz' 的评论中的 '回复: @东明朗春 (点击查看)'")
    print("   2. 应该显示正确的对话:")
    print("      - 原始评论: 东明朗春 - '异安朋友们多睡会儿呀'")
    print("      - 回复评论: 佳佳子_zz - '哈哈'")
    print("   3. 而不是显示东明朗春的其他评论")
    
    print("\n💡 修复说明:")
    print("   - 现在使用 '父评论ID' 字段精确匹配一级评论和二级评论")
    print("   - 如果父评论ID不可用，才回退到按用户名查找的备用方案")
    print("   - 这确保了二级评论和一级评论的精确对应关系")
    
    print("\n按 Ctrl+C 停止服务器")
    
    # 保持服务器运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 停止服务器")

if __name__ == "__main__":
    asyncio.run(test_reply_logic())