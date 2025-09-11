#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速启动脚本：CSV数据导入与Web监控
简化用户操作，一键启动完整功能
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from tools.csv_importer import CSVImporter
from tools import utils


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    📊 MediaCrawler Web监控启动器 📊                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  功能：                                                                      ║
║  ✅ CSV数据导入到Web可视化界面                                               ║
║  ✅ 实时评论监控（8081端口）                                                 ║
║  ✅ 数据可视化分析与导出                                                     ║
║  ✅ 自动词云生成与情感分析                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


async def main():
    """主函数"""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='MediaCrawler Web监控启动器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 自动查找并导入最新CSV数据
  python start_web_monitor.py --auto
  
  # 指定CSV文件路径
  python start_web_monitor.py --csv "data/douyin/comments_20231201.csv"
  
  # 启动完整抓取+监控流程
  python start_web_monitor.py --full-crawl
        """
    )
    
    parser.add_argument(
        '--csv', 
        type=str, 
        help='指定CSV文件路径'
    )
    
    parser.add_argument(
        '--platform', 
        type=str, 
        default='douyin',
        choices=['douyin', 'dy', 'xiaohongshu', 'xhs', 'kuaishou', 'ks'],
        help='平台名称 (默认: douyin)'
    )
    
    parser.add_argument(
        '--auto', 
        action='store_true',
        help='自动查找最新的CSV文件并导入'
    )
    
    parser.add_argument(
        '--full-crawl',
        action='store_true', 
        help='启动完整的抓取+监控流程（需要配置视频ID）'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8081,
        help='Web服务器端口 (默认: 8081)'
    )
    
    args = parser.parse_args()
    
    if args.full_crawl:
        print("🚀 启动完整抓取+监控流程...")
        print("📝 请确保已在 config/base_config.py 中配置了视频ID")
        print("💡 建议运行: uv run main.py --platform dy --lt qrcode --type detail --save_data_option web")
        return
    
    # CSV导入模式
    importer = CSVImporter()
    csv_file_path = args.csv
    
    # 自动查找CSV文件
    if args.auto or not csv_file_path:
        print("🔍 正在查找最新的CSV文件...")
        csv_file_path = importer.find_latest_csv(args.platform)
        if not csv_file_path:
            print("❌ 未找到CSV文件")
            print("\n💡 请先运行以下命令生成CSV数据：")
            print("   uv run main.py --platform dy --lt qrcode --type detail --save_data_option csv")
            print("\n或者手动指定CSV文件路径：")
            print("   python start_web_monitor.py --csv \"your_csv_file.csv\"")
            return
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV文件不存在: {csv_file_path}")
        return
    
    print(f"📁 找到CSV文件: {csv_file_path}")
    
    # 显示配置信息
    print(f"\n⚙️  配置信息:")
    print(f"   📄 CSV文件: {csv_file_path}")
    print(f"   🎯 平台: {args.platform}")
    print(f"   🌐 Web端口: {args.port}")
    
    print(f"\n📊 开始导入CSV数据到Web监控界面...")
    
    # 执行导入
    success = await importer.import_csv_to_web(csv_file_path, args.platform)
    
    if success:
        print("\n✅ CSV数据导入成功!")
        print(f"🌐 Web界面地址: http://localhost:{args.port}")
        print("📊 数据可视化界面已启动")
        print("\n🎉 功能特性:")
        print("   • 实时数据统计与图表")
        print("   • 评论情感分析")
        print("   • 词云生成")
        print("   • 数据导出（CSV/Excel）")
        print("   • 地理位置分布")
        print("   • 活跃用户排行")
        
        print(f"\n⏰ Web服务器将持续运行...")
        print("   💡 按 Ctrl+C 停止服务")
        print("   🔄 数据会实时更新显示")
        
        # 保持程序运行
        try:
            # 每30秒显示一次状态
            count = 0
            while True:
                await asyncio.sleep(30)
                count += 1
                print(f"✨ Web服务运行中... ({count * 30}秒) - http://localhost:{args.port}")
        except KeyboardInterrupt:
            print("\n👋 Web服务已停止")
    else:
        print("❌ CSV数据导入失败")
        print("\n🔧 故障排除建议:")
        print("   1. 检查CSV文件格式是否正确")
        print("   2. 确认端口是否被占用")
        print("   3. 查看错误日志信息")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        print("💡 请检查配置或查看日志")