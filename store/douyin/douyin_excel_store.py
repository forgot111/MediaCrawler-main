# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 18:46
# @Desc    : 抖音Excel增强存储实现类

import asyncio
import os
import pathlib
from typing import Dict, List
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import BarChart, Reference, LineChart, PieChart

import config
from base.base_crawler import AbstractStore
from tools import utils
from var import crawler_type_var


class DouyinExcelStoreImplement(AbstractStore):
    """抖音Excel增强存储实现类 - 带格式化和图表"""
    
    def __init__(self):
        self.excel_store_path = "data/douyin/excel"
        self.data_cache = {
            'contents': [],
            'comments': [],
            'creators': []
        }
        self.lock = asyncio.Lock()
        
    async def store_content(self, content_item: Dict):
        """存储内容"""
        async with self.lock:
            self.data_cache['contents'].append(content_item)

    async def store_comment(self, comment_item: Dict):
        """存储评论"""
        async with self.lock:
            self.data_cache['comments'].append(comment_item)
            
            # 每100条评论生成一次Excel报告
            if len(self.data_cache['comments']) % 100 == 0:
                await self._generate_excel_report()

    async def store_creator(self, creator: Dict):
        """存储创作者信息"""
        async with self.lock:
            self.data_cache['creators'].append(creator)

    async def _generate_excel_report(self):
        """生成格式化的Excel报告"""
        try:
            pathlib.Path(self.excel_store_path).mkdir(parents=True, exist_ok=True)
            
            if not self.data_cache['comments']:
                return
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_file = f'{self.excel_store_path}/douyin_analysis_{timestamp}.xlsx'
            
            # 创建工作簿
            wb = Workbook()
            
            # 删除默认工作表
            wb.remove(wb.active)
            
            # 创建评论数据工作表
            await self._create_comments_sheet(wb)
            
            # 创建统计分析工作表
            await self._create_statistics_sheet(wb)
            
            # 创建内容数据工作表（如果有数据）
            if self.data_cache['contents']:
                await self._create_contents_sheet(wb)
                
            # 保存文件
            wb.save(excel_file)
            
            utils.logger.info(f"[DouyinExcelStore] 已生成Excel报告: {excel_file}")
            
        except Exception as e:
            utils.logger.error(f"[DouyinExcelStore] 生成Excel报告失败: {e}")

    async def _create_comments_sheet(self, wb):
        """创建评论数据工作表"""
        ws = wb.create_sheet(title="评论数据")
        
        # 转换为DataFrame
        df = pd.DataFrame(self.data_cache['comments'])
        
        # 设置表头样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # 添加数据到工作表
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        # 设置表头格式
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 设置列宽
        column_widths = {
            'A': 20,  # 评论时间
            'B': 15,  # 用户昵称
            'C': 50,  # 评论内容
            'D': 10,  # 点赞数
            'E': 15,  # 被回复人昵称
            'F': 30,  # 被回复人原先的内容
            'G': 8,   # 作者已赞
            'H': 15,  # ip归属
        }
        
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        # 设置边框
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for row in ws.iter_rows():
            for cell in row:
                cell.border = thin_border
                if cell.row > 1:  # 非表头行
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
        
        # 冻结首行
        ws.freeze_panes = "A2"
        
        # 添加筛选器
        ws.auto_filter.ref = ws.dimensions

    async def _create_statistics_sheet(self, wb):
        """创建统计分析工作表"""
        ws = wb.create_sheet(title="数据分析")
        
        df = pd.DataFrame(self.data_cache['comments'])
        
        # 标题
        ws['A1'] = "抖音评论数据分析报告"
        ws['A1'].font = Font(size=16, bold=True, color="366092")
        ws.merge_cells('A1:E1')
        
        # 基础统计
        row = 3
        stats = [
            ("总评论数", len(df)),
            ("参与用户数", df['用户昵称'].nunique() if '用户昵称' in df.columns else 0),
            ("总点赞数", int(pd.to_numeric(df['点赞数'], errors='coerce').sum()) if '点赞数' in df.columns else 0),
            ("平均点赞数", round(pd.to_numeric(df['点赞数'], errors='coerce').mean(), 2) if '点赞数' in df.columns else 0),
            ("地区分布数", df['ip归属'].nunique() if 'ip归属' in df.columns else 0),
        ]
        
        ws[f'A{row}'] = "基础统计"
        ws[f'A{row}'].font = Font(bold=True, color="366092")
        row += 1
        
        for stat_name, stat_value in stats:
            ws[f'A{row}'] = stat_name
            ws[f'B{row}'] = stat_value
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
        
        row += 2
        
        # 热门评论Top10
        if '点赞数' in df.columns and len(df) > 0:
            ws[f'A{row}'] = "热门评论Top10"
            ws[f'A{row}'].font = Font(bold=True, color="366092")
            row += 1
            
            # 表头
            headers = ["排名", "用户昵称", "评论内容", "点赞数"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col)
                cell.value = header
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
            row += 1
            
            # 热门评论数据
            top_comments = df.nlargest(10, '点赞数')
            for idx, (_, comment) in enumerate(top_comments.iterrows(), 1):
                ws[f'A{row}'] = idx
                ws[f'B{row}'] = comment.get('用户昵称', 'N/A')
                content = str(comment.get('评论内容', ''))
                ws[f'C{row}'] = content[:100] + '...' if len(content) > 100 else content
                ws[f'D{row}'] = comment.get('点赞数', 0)
                row += 1
        
        row += 2
        
        # 活跃用户Top10
        if '用户昵称' in df.columns and len(df) > 0:
            ws[f'A{row}'] = "活跃用户Top10"
            ws[f'A{row}'].font = Font(bold=True, color="366092")
            row += 1
            
            # 表头
            headers = ["排名", "用户昵称", "评论数量", "平均点赞数"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col)
                cell.value = header
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
            row += 1
            
            # 活跃用户数据
            user_stats = df.groupby('用户昵称').agg({
                '评论内容': 'count',
                '点赞数': lambda x: pd.to_numeric(x, errors='coerce').mean()
            }).sort_values('评论内容', ascending=False).head(10)
            
            for idx, (user, stats) in enumerate(user_stats.iterrows(), 1):
                ws[f'A{row}'] = idx
                ws[f'B{row}'] = user
                ws[f'C{row}'] = stats['评论内容']
                ws[f'D{row}'] = round(stats['点赞数'], 2)
                row += 1
        
        # 设置列宽
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 60
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 15

    async def _create_contents_sheet(self, wb):
        """创建内容数据工作表"""
        ws = wb.create_sheet(title="视频数据")
        
        # 转换为DataFrame
        df = pd.DataFrame(self.data_cache['contents'])
        
        # 设置表头样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # 添加数据到工作表
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        # 设置表头格式
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 设置列宽
        ws.column_dimensions['A'].width = 20  # aweme_id
        ws.column_dimensions['B'].width = 15  # aweme_type
        ws.column_dimensions['C'].width = 50  # title
        ws.column_dimensions['D'].width = 20  # 发布时间
        ws.column_dimensions['E'].width = 15  # nickname
        ws.column_dimensions['F'].width = 12  # liked_count
        ws.column_dimensions['G'].width = 12  # comment_count
        
        # 冻结首行
        ws.freeze_panes = "A2"
        
        # 添加筛选器
        ws.auto_filter.ref = ws.dimensions

    async def generate_final_excel_report(self):
        """生成最终完整Excel报告"""
        try:
            await self._generate_excel_report()
            utils.logger.info(f"[DouyinExcelStore] 最终Excel报告已生成完成！")
            
        except Exception as e:
            utils.logger.error(f"[DouyinExcelStore] 生成最终Excel报告失败: {e}")