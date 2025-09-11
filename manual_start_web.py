#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动启动Web服务器并导入CSV数据
用于测试和调试Web界面
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import utils
from tools.csv_importer import CSVImporter
from store.douyin.douyin_web_store import DouyinWebStoreImplement

async def main():
    """手动启动Web服务器并导入CSV数据"""
    try:
        print("🚀 手动启动抖音Web监控界面")
        
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
        
        if not csv_file_path:
            # 如果没找到，尝试默认方法
            csv_file_path = csv_importer.find_latest_csv("douyin")
        
        if csv_file_path and os.path.exists(csv_file_path):
            print(f"📁 读取CSV文件: {csv_file_path}")
            
            # 读取CSV数据
            comments = await csv_importer._read_csv_data(csv_file_path)
            
            if comments:
                print(f"📊 读取到 {len(comments)} 条评论数据")
                
                # 批量导入到Web界面
                await web_store.bulk_import_comments(comments, analyze_after=True)
                
                print("✅ CSV数据导入Web界面成功")
                print("🌐 Web监控界面已启动: http://localhost:8082")
                print("📝 请在浏览器中访问上述地址查看数据")
                print("⚠️  按 Ctrl+C 停止服务器")
                
                # 保持程序运行
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n👋 服务器已停止")
            else:
                print("❌ CSV文件为空或读取失败")
        else:
            print("❌ 未找到CSV文件")
            
            # 即使没有数据也启动Web服务器
            await web_store.bulk_import_comments([], analyze_after=False)
            print("🌐 空的Web监控界面已启动: http://localhost:8082")
            
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 服务器已停止")
                
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎯 启动抖音Web监控界面...")
    asyncio.run(main())