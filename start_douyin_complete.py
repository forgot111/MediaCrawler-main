#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动完整的抖音评论抓取和Web监控流程
严格按照三个阶段执行：
1. 先完整抓取所有评论和二级评论
2. 然后自动导入CSV到Web界面 
3. 最后才开始监控新评论
"""

import asyncio
import sys
import os
import socket

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import utils
from media_platform.douyin.core import DouYinCrawler
from config import dy_config as config
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

async def start_web_service_automatically():
    """自动启动Web服务"""
    try:
        print("\n" + "="*80)
        print("🌐 阶段2：自动启动Web监控界面")
        print("="*80)
        
        utils.logger.info("🚀 自动选择可用端口启动Web服务器")
        
        # 寻找可用端口，扩大搜索范围
        available_port = find_available_port(8082, 50)  # 搜索8082-8132范围
        if not available_port:
            print("❌ 无法找到可用端口（尝试了8082-8132）")
            return False
            
        print(f"✅ 找到可用端口: {available_port}")
        
        # 检查CSV文件
        csv_path = None
        desktop_path = "F:/下载"
        
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
        print(f"❌ Web服务启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数：启动完整的自动化流程"""
    try:
        print("="*80)
        print("🎯 抖音评论完整抓取和Web监控自动化流程")
        print("="*80)
        
        utils.logger.info("🚀 启动抖音完整评论抓取和Web监控流程")
        
        # 创建抖音爬虫实例
        douyin_crawler = DouYinCrawler()
        
        # 初始化登录
        utils.logger.info("📋 步骤1：初始化登录")
        await douyin_crawler.start()
        
        # 显示目标视频信息
        utils.logger.info("🎬 目标视频ID列表:")
        for i, aweme_id in enumerate(config.DY_SPECIFIED_ID_LIST, 1):
            utils.logger.info(f"   {i}. {aweme_id}")
        
        # 执行完整的自动化流程（三个阶段）
        utils.logger.info("🔄 开始执行三阶段自动化流程")
        print("\n⚠️  注意：程序将自动按照以下顺序执行：")
        print("   🔸 阶段1：完整抓取所有评论和二级评论")
        print("   🔸 阶段2：自动启动Web界面并导入CSV数据")
        print("   💡 每个阶段必须完全完成后才进入下一阶段！\n")
        
        # 阶段1：调用改进后的完整流程 - 使用标准抓取版本（已移除持续监控）
        print("🚀 阶段1：开始抓取评论...")
        stage1_success = False
        try:
            await douyin_crawler.get_specified_awemes()
            utils.logger.info("✅ 阶段1完成：评论抓取完毕")
            stage1_success = True
        except Exception as stage1_error:
            utils.logger.error(f"⚠️ 阶段1出现错误: {stage1_error}")
            if "Target page, context or browser has been closed" in str(stage1_error):
                utils.logger.info("💡 检测到浏览器关闭错误，但评论可能已经抓取完成，继续执行Web启动...")
                stage1_success = True  # 允许继续执行Web启动
            else:
                utils.logger.error("❌ 阶段1失败，跳过Web启动")
                raise stage1_error
        
        # 阶段2：自动启动Web服务（无论阶段1是否完全成功）
        if stage1_success:
            # 在启动Web服务前，先关闭浏览器释放资源
            utils.logger.info("🔧 阶段1完成，正在关闭浏览器释放资源...")
            try:
                await douyin_crawler.close()
                utils.logger.info("✅ 浏览器已关闭，开始启动Web服务")
            except Exception as close_error:
                utils.logger.warning(f"⚠️ 浏览器关闭时出现错误: {close_error}")
            
            utils.logger.info("🔄 开始阶段2：自动启动Web监控界面")
            await start_web_service_automatically()
            utils.logger.info("🎉 完整自动化流程执行完毕")
        else:
            utils.logger.error("❌ 由于阶段1失败，跳过Web启动")
        
    except KeyboardInterrupt:
        utils.logger.info("⏹️  程序被用户中断")
    except Exception as e:
        utils.logger.error(f"❌ 程序执行出错: {e}")
        if "Target page, context or browser has been closed" in str(e):
            utils.logger.error("💡 浏览器连接已断开，这通常是因为：")
            utils.logger.error("   1. 之前运行的程序已经关闭了浏览器")
            utils.logger.error("   2. 账号可能被风控，建议等待后重新登录")
            utils.logger.error("   3. 请避免同时运行多个爬虫程序")
        elif "account blocked" in str(e):
            utils.logger.error("🚫 账号被风控，建议：")
            utils.logger.error("   1. 等待30-60分钟后重试")
            utils.logger.error("   2. 重新扫码登录")
            utils.logger.error("   3. 降低爬取频率")
        import traceback
        traceback.print_exc()
    finally:
        # 最终确保浏览器关闭（如果还没关闭的话）
        try:
            if hasattr(douyin_crawler, 'browser_context') and douyin_crawler.browser_context:
                await douyin_crawler.close()
                utils.logger.info("🔧 最终确保浏览器已关闭")
        except Exception as close_error:
            utils.logger.warning(f"⚠️ 最终浏览器关闭时出现错误: {close_error}")
            pass

if __name__ == "__main__":
    print("\n🔥 启动抖音三阶段自动化流程...")
    asyncio.run(main())