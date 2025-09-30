# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
CSV数据导入工具
用于将已有的CSV评论数据导入到Web监控界面中
"""

import os
import csv
import asyncio
import argparse
from typing import List, Dict
from pathlib import Path

from tools import utils


class CSVImporter:
    """CSV数据导入器"""
    
    def __init__(self):
        self.data_dir = Path("data")
        
    async def import_csv_to_web(self, csv_file_path: str, platform: str = "douyin"):
        """
        将CSV文件导入到Web监控界面
        
        Args:
            csv_file_path: CSV文件路径
            platform: 平台名称 (douyin, xhs, kuaishou等)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(csv_file_path):
                utils.logger.error(f"[CSVImporter] CSV文件不存在: {csv_file_path}")
                return False
                
            # 读取CSV数据
            comments = await self._read_csv_data(csv_file_path)
            if not comments:
                utils.logger.error(f"[CSVImporter] 未能从CSV文件读取到有效数据")
                return False
                
            utils.logger.info(f"[CSVImporter] 成功读取 {len(comments)} 条评论数据")
            
            # 根据平台创建对应的Web存储实例
            web_store = await self._create_web_store(platform)
            if not web_store:
                utils.logger.error(f"[CSVImporter] 不支持的平台: {platform}")
                return False
                
            # 启用轻量模式以提高导入速度
            web_store.set_light_mode(True)
            
            # 批量导入评论数据
            utils.logger.info(f"[CSVImporter] 开始批量导入评论数据到Web界面...")
            await web_store.bulk_import_comments(comments, analyze_after=True)
            
            # 关闭轻量模式，进行完整分析
            web_store.set_light_mode(False)
            
            utils.logger.info(f"[CSVImporter] CSV数据导入完成!")
            utils.logger.info(f"[CSVImporter] 请访问 http://localhost:8081 查看数据可视化界面")
            
            return True
            
        except Exception as e:
            utils.logger.error(f"[CSVImporter] 导入失败: {e}")
            return False
    
    async def _read_csv_data(self, csv_file_path: str) -> List[Dict]:
        """读取CSV文件数据"""
        comments = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig', newline='') as file:
                # 尝试多种方式读取CSV
                try:
                    # 首先尝试自动检测
                    sample = file.read(2048)
                    file.seek(0)
                    dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
                    reader = csv.DictReader(file, dialect=dialect)
                except Exception:
                    # 如果自动检测失败，使用默认逗号分隔符
                    file.seek(0)
                    reader = csv.DictReader(file, delimiter=',')
                
                for row_num, row in enumerate(reader, start=1):
                    try:
                        # 数据清理和标准化
                        comment = {}
                        for key, value in row.items():
                            if key and key.strip():
                                # 去除BOM和空白字符
                                clean_key = key.strip().replace('\ufeff', '')
                                clean_value = str(value).strip() if value else ''
                                comment[clean_key] = clean_value
                        
                        # 只有当评论有基本字段时才添加
                        if comment and ('评论内容' in comment or '用户昵称' in comment):
                            comments.append(comment)
                    except Exception as row_error:
                        utils.logger.warning(f"[CSVImporter] 跳过第 {row_num} 行数据，错误: {row_error}")
                        continue
                        
        except Exception as e:
            utils.logger.error(f"[CSVImporter] 读取CSV文件失败: {e}")
            # 尝试备用方法：逐行读取并手动解析
            try:
                utils.logger.info(f"[CSVImporter] 尝试备用解析方法...")
                comments = await self._fallback_csv_parse(csv_file_path)
            except Exception as fallback_error:
                utils.logger.error(f"[CSVImporter] 备用解析也失败: {fallback_error}")
            
        return comments
    
    async def _fallback_csv_parse(self, csv_file_path: str) -> List[Dict]:
        """备用CSV解析方法：手动逐行解析"""
        comments = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
                lines = file.readlines()
                if not lines:
                    return []
                
                # 获取表头
                header_line = lines[0].strip()
                headers = [h.strip() for h in header_line.split(',')]
                
                utils.logger.info(f"[CSVImporter] 检测到CSV表头: {headers[:5]}...")
                
                # 解析数据行
                for line_num, line in enumerate(lines[1:], start=2):
                    try:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # 简单的逗号分割（可能不完美，但比完全失败要好）
                        values = line.split(',')
                        
                        # 创建字典
                        comment = {}
                        for i, header in enumerate(headers):
                            if i < len(values):
                                comment[header] = values[i].strip()
                            else:
                                comment[header] = ''
                        
                        # 只添加有内容的评论
                        if comment.get('评论内容', '').strip() or comment.get('用户昵称', '').strip():
                            comments.append(comment)
                            
                    except Exception as row_error:
                        utils.logger.warning(f"[CSVImporter] 备用解析跳过第 {line_num} 行: {row_error}")
                        continue
                        
        except Exception as e:
            utils.logger.error(f"[CSVImporter] 备用CSV解析失败: {e}")
            
        return comments
    
    async def _create_web_store(self, platform: str):
        """根据平台创建对应的Web存储实例"""
        try:
            if platform.lower() in ['douyin', 'dy']:
                from store.douyin.douyin_web_store import DouyinWebStoreImplement
                return DouyinWebStoreImplement()
            elif platform.lower() in ['xiaohongshu', 'xhs']:
                # 如果有小红书Web存储实现，可以在这里添加
                utils.logger.warning(f"[CSVImporter] 小红书Web存储暂未实现，使用抖音存储")
                from store.douyin.douyin_web_store import DouyinWebStoreImplement
                return DouyinWebStoreImplement()
            elif platform.lower() in ['kuaishou', 'ks']:
                # 如果有快手Web存储实现，可以在这里添加
                utils.logger.warning(f"[CSVImporter] 快手Web存储暂未实现，使用抖音存储")
                from store.douyin.douyin_web_store import DouyinWebStoreImplement
                return DouyinWebStoreImplement()
            else:
                utils.logger.warning(f"[CSVImporter] 未知平台 {platform}，使用抖音存储")
                from store.douyin.douyin_web_store import DouyinWebStoreImplement
                return DouyinWebStoreImplement()
                
        except Exception as e:
            utils.logger.error(f"[CSVImporter] 创建Web存储实例失败: {e}")
            return None
    
    def find_latest_csv(self, platform: str = "douyin") -> str:
        """查找最新的CSV文件"""
        try:
            # 首先在D桌面查找（抽取数据的输出位置）
            desktop_csv = self._find_latest_csv_in_desktop()
            if desktop_csv:
                return desktop_csv
            
            # 如果桌面没有，再在默认data目录查找
            platform_dir = self.data_dir / platform
            if not platform_dir.exists():
                utils.logger.error(f"[CSVImporter] 平台数据目录不存在: {platform_dir}")
                return ""
                
            # 查找所有CSV文件
            csv_files = list(platform_dir.glob("*.csv"))
            if not csv_files:
                utils.logger.error(f"[CSVImporter] 未找到CSV文件: {platform_dir}")
                return ""
                
            # 按修改时间排序，返回最新的
            latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
            utils.logger.info(f"[CSVImporter] 找到最新CSV文件: {latest_csv}")
            return str(latest_csv)
            
        except Exception as e:
            utils.logger.error(f"[CSVImporter] 查找CSV文件失败: {e}")
            return ""
    
    def _find_latest_csv_in_desktop(self) -> str:
        """在D桌面查找最新的CSV文件"""
        try:
            import glob
            
            # 在D盘桌面查找CSV文件
            desktop_path = "F:/下载"
            if not os.path.exists(desktop_path):
                return ""
                
            # 查找所有CSV文件
            csv_files = glob.glob(os.path.join(desktop_path, "*.csv"))
            if not csv_files:
                return ""
                
            # 返回最新的CSV文件
            latest_csv = max(csv_files, key=lambda f: os.path.getmtime(f))
            utils.logger.info(f"[CSVImporter] 在桌面找到CSV文件: {latest_csv}")
            return latest_csv
            
        except Exception as e:
            utils.logger.error(f"[CSVImporter] 查找桌面CSV文件失败: {e}")
            return ""


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='CSV数据导入到Web监控界面')
    parser.add_argument('--csv', type=str, help='CSV文件路径')
    parser.add_argument('--platform', type=str, default='douyin', choices=['douyin', 'dy', 'xiaohongshu', 'xhs', 'kuaishou', 'ks'], help='平台名称')
    parser.add_argument('--auto', action='store_true', help='自动查找最新的CSV文件')
    
    args = parser.parse_args()
    
    importer = CSVImporter()
    
    csv_file_path = args.csv
    
    # 如果启用自动模式或未指定CSV文件，则查找最新的
    if args.auto or not csv_file_path:
        csv_file_path = importer.find_latest_csv(args.platform)
        if not csv_file_path:
            print("❌ 未找到CSV文件")
            return
    
    print(f"📊 开始导入CSV数据到Web监控界面...")
    print(f"📁 CSV文件: {csv_file_path}")
    print(f"🎯 平台: {args.platform}")
    
    success = await importer.import_csv_to_web(csv_file_path, args.platform)
    
    if success:
        print("✅ CSV数据导入成功!")
        print("🌐 请访问 http://localhost:8081 查看数据可视化界面")
        print("⏰ Web服务器将持续运行，按 Ctrl+C 停止")
        
        # 保持程序运行
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("\n👋 程序已停止")
    else:
        print("❌ CSV数据导入失败")


if __name__ == "__main__":
    asyncio.run(main())