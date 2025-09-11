#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据导入功能
"""

import asyncio
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import utils
from tools.csv_importer import CSVImporter
from store.douyin.douyin_web_store import DouyinWebStoreImplement

async def test_data_import():
    """测试数据导入功能"""
    try:
        print("🧪 测试数据导入功能")
        
        # 创建Web存储实例
        web_store = DouyinWebStoreImplement()
        
        # 查找CSV文件
        csv_importer = CSVImporter()
        
        # 首先检查桌面的视频ID格式文件
        import glob
        desktop_paths = ["D:/桌面", "D:/Desktop", os.path.expanduser("~/Desktop")]
        csv_file_path = None
        
        for desktop_path in desktop_paths:
            if os.path.exists(desktop_path):
                print(f"🔍 检查目录: {desktop_path}")
                csv_files = glob.glob(os.path.join(desktop_path, "*.csv"))
                
                # 查找视频ID格式的CSV文件
                video_id_csv_files = []
                for csv_file in csv_files:
                    filename = os.path.basename(csv_file)
                    if filename[0].isdigit() and filename.endswith('_comments.csv'):
                        video_id_csv_files.append(csv_file)
                
                if video_id_csv_files:
                    csv_file_path = max(video_id_csv_files, key=lambda f: os.path.getmtime(f))
                    print(f"✅ 找到CSV文件: {csv_file_path}")
                    break
        
        if csv_file_path and os.path.exists(csv_file_path):
            print(f"📁 读取CSV文件: {csv_file_path}")
            
            # 读取CSV数据
            comments = await csv_importer._read_csv_data(csv_file_path)
            
            if comments:
                print(f"📊 读取到 {len(comments)} 条评论数据")
                print(f"📝 第一条评论示例: {comments[0]}")
                
                # 手动测试数据导入
                print("🧪 开始测试数据导入到data_cache...")
                
                # 直接操作data_cache
                web_store.data_cache['comments'].extend(comments)
                print(f"📋 data_cache中评论数量: {len(web_store.data_cache['comments'])}")
                
                # 更新统计信息
                await web_store._update_statistics()
                print(f"📊 统计信息更新完成")
                
                # 手动保存到文件
                await web_store._update_web_data()
                print(f"💾 数据文件更新完成")
                
                # 验证文件内容
                data_file_path = os.path.join(web_store.web_path, "data.json")
                if os.path.exists(data_file_path):
                    with open(data_file_path, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    
                    print(f"✅ 验证结果:")
                    print(f"   - 文件中评论数量: {len(saved_data.get('comments', []))}")
                    print(f"   - 统计信息总评论数: {saved_data.get('stats', {}).get('total_comments', 0)}")
                    print(f"   - 作者点赞数: {saved_data.get('stats', {}).get('author_liked_count', 0)}")
                    
                    if len(saved_data.get('comments', [])) > 0:
                        print(f"✅ 数据导入成功！")
                        return True
                    else:
                        print(f"❌ 数据导入失败：文件中评论数量为0")
                        return False
                else:
                    print(f"❌ 数据文件不存在: {data_file_path}")
                    return False
            else:
                print("❌ CSV文件为空或读取失败")
                return False
        else:
            print("❌ 未找到CSV文件")
            return False
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 开始测试数据导入功能...")
    result = asyncio.run(test_data_import())
    print(f"🏁 测试结果: {'成功' if result else '失败'}")