#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复统计信息
"""

import asyncio
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from store.douyin.douyin_web_store import DouyinWebStoreImplement

async def fix_stats():
    """修复统计信息"""
    try:
        print("🔧 修复统计信息...")
        
        # 创建Web存储实例
        web_store = DouyinWebStoreImplement()
        
        # 检查是否有数据文件
        data_file_path = os.path.join(web_store.web_path, "data.json")
        if os.path.exists(data_file_path):
            print(f"📁 加载现有数据文件: {data_file_path}")
            with open(data_file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # 将现有评论加载到缓存
            comments = existing_data.get('comments', [])
            if comments:
                print(f"📊 找到 {len(comments)} 条评论")
                web_store.data_cache['comments'] = comments
                
                # 强制更新统计信息
                print("📈 重新计算统计信息...")
                await web_store._update_statistics()
                
                # 强制更新分析数据
                print("📊 重新计算分析数据...")
                await web_store._update_analytics()
                
                # 保存到文件
                print("💾 保存更新后的数据...")
                await web_store._update_web_data()
                
                # 验证结果
                with open(data_file_path, 'r', encoding='utf-8') as f:
                    updated_data = json.load(f)
                
                print(f"✅ 修复完成:")
                print(f"   - 评论数量: {len(updated_data.get('comments', []))}")
                print(f"   - 统计信息: {updated_data.get('stats', {})}")
                print(f"   - 作者赞过评论数: {updated_data.get('stats', {}).get('author_liked_count', 0)}")
                
                return True
            else:
                print("❌ 数据文件中没有评论")
                return False
        else:
            print(f"❌ 数据文件不存在: {data_file_path}")
            return False
            
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 开始修复统计信息...")
    result = asyncio.run(fix_stats())
    print(f"🏁 修复结果: {'成功' if result else '失败'}")