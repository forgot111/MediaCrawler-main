#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能启动Web服务器 - 自动选择可用端口
"""

import asyncio
import sys
import os
import socket

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from store.douyin.douyin_web_store import DouyinWebStoreImplement

def is_port_available(port):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('localhost', port))
            return True
    except OSError:
        return False

def find_available_port(start_port=8082, max_tries=20):
    """寻找可用端口"""
    port = start_port
    for _ in range(max_tries):
        if is_port_available(port):
            return port
        port += 1
    return None

async def start_web_with_auto_port():
    """启动Web服务器并自动选择端口"""
    try:
        print("🎯 智能启动抖音Web监控界面...")
        print("🚀 自动选择可用端口启动Web服务器")
        
        # 寻找可用端口
        available_port = find_available_port(8082)
        if not available_port:
            print("❌ 无法找到可用端口（尝试了8082-8102）")
            return False
            
        print(f"✅ 找到可用端口: {available_port}")
        
        # 检查CSV文件
        csv_path = None
        desktop_path = "D:/桌面"
        
        print(f"🔍 检查目录: {desktop_path}")
        if os.path.exists(desktop_path):
            for file in os.listdir(desktop_path):
                if file.endswith('_comments.csv'):
                    csv_path = os.path.join(desktop_path, file)
                    print(f"✅ 找到CSV文件: {csv_path}")
                    break
        
        if not csv_path:
            print("❌ 未找到CSV评论文件")
            return False
        
        # 创建Web存储实例
        web_store = DouyinWebStoreImplement()
        
        # 修改端口配置
        web_store.port = available_port
        
        # 读取CSV文件
        print(f"📁 读取CSV文件: {csv_path}")
        import pandas as pd
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"📊 读取到 {len(df)} 条评论数据")
        
        # 清理数据，将NaN和无效值替换为合适的默认值
        df = df.fillna('')  # 将所有NaN替换为空字符串
        
        # 确保数值字段为数字类型
        numeric_columns = ['点赞数', '子评论数', '父评论ID', '评论ID', '视频ID', '用户ID']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # 转换为字典列表
        comments = df.to_dict('records')
        
        # 导入评论数据
        await web_store.bulk_import_comments(comments, analyze_after=True)
        
        print("✅ CSV数据导入Web界面成功")
        print(f"🌐 Web监控界面已启动: http://localhost:{available_port}")
        print("📝 请在浏览器中访问上述地址查看数据")
        print("⚠️  按 Ctrl+C 停止服务器")
        
        # 保持服务器运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Web服务器已停止")
            return True
            
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 开始智能启动Web服务器...")
    result = asyncio.run(start_web_with_auto_port())
    print(f"🏁 启动结果: {'成功' if result else '失败'}")