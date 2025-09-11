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

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import utils
from media_platform.douyin.core import DouYinCrawler
from config import dy_config as config

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
        print("\n⚠️  注意：程序将严格按照以下顺序执行：")
        print("   🔸 阶段1：完整抓取所有评论和二级评论")
        print("   🔸 阶段2：自动导入CSV数据到Web界面")
        print("   🔸 阶段3：开始持续监控新评论")
        print("   💡 每个阶段必须完全完成后才进入下一阶段！\n")
        
        # 调用改进后的完整流程 - 使用带Web监控的版本
        await douyin_crawler.get_specified_awemes_with_web_monitoring()
        
        utils.logger.info("🎉 三阶段自动化流程完成")
        
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
        try:
            await douyin_crawler.close()
        except:
            pass

if __name__ == "__main__":
    print("\n🔥 启动抖音三阶段自动化流程...")
    asyncio.run(main())