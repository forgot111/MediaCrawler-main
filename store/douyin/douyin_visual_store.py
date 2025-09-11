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
# @Desc    : 抖音数据可视化存储实现类

import asyncio
import json
import os
import pathlib
from typing import Dict, List
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import jieba
from collections import Counter
import re

import aiofiles
import config
from base.base_crawler import AbstractStore
from tools import utils
from var import crawler_type_var


class DouyinVisualStoreImplement(AbstractStore):
    """抖音数据可视化存储实现类"""
    
    def __init__(self):
        self.output_path = "data/douyin/visual"
        self.data_cache = {
            'contents': [],
            'comments': [],
            'creators': []
        }
        self.lock = asyncio.Lock()
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
    async def store_content(self, content_item: Dict):
        """存储内容并生成内容统计图表"""
        async with self.lock:
            self.data_cache['contents'].append(content_item)
            # 每10条内容生成一次图表
            if len(self.data_cache['contents']) % 10 == 0:
                await self._generate_content_charts()

    async def store_comment(self, comment_item: Dict):
        """存储评论并生成评论分析图表"""
        async with self.lock:
            self.data_cache['comments'].append(comment_item)
            # 每50条评论生成一次图表
            if len(self.data_cache['comments']) % 50 == 0:
                await self._generate_comment_charts()

    async def store_creator(self, creator: Dict):
        """存储创作者信息"""
        async with self.lock:
            self.data_cache['creators'].append(creator)

    async def _generate_content_charts(self):
        """生成内容相关图表"""
        try:
            pathlib.Path(self.output_path).mkdir(parents=True, exist_ok=True)
            
            if not self.data_cache['contents']:
                return
                
            df = pd.DataFrame(self.data_cache['contents'])
            
            # 1. 点赞数分布图
            plt.figure(figsize=(12, 8))
            
            plt.subplot(2, 2, 1)
            likes = pd.to_numeric(df['liked_count'], errors='coerce').fillna(0)
            plt.hist(likes, bins=20, alpha=0.7, color='skyblue')
            plt.title('视频点赞数分布')
            plt.xlabel('点赞数')
            plt.ylabel('视频数量')
            
            # 2. 评论数分布图
            plt.subplot(2, 2, 2)
            comments = pd.to_numeric(df['comment_count'], errors='coerce').fillna(0)
            plt.hist(comments, bins=20, alpha=0.7, color='lightgreen')
            plt.title('视频评论数分布')
            plt.xlabel('评论数')
            plt.ylabel('视频数量')
            
            # 3. 发布时间趋势
            plt.subplot(2, 2, 3)
            if '发布时间' in df.columns:
                df['发布时间'] = pd.to_datetime(df['发布时间'])
                df['发布日期'] = df['发布时间'].dt.date
                daily_counts = df['发布日期'].value_counts().sort_index()
                plt.plot(daily_counts.index, daily_counts.values, marker='o')
                plt.title('视频发布时间趋势')
                plt.xlabel('日期')
                plt.ylabel('发布数量')
                plt.xticks(rotation=45)
            
            # 4. IP归属地分布
            plt.subplot(2, 2, 4)
            if 'ip_location' in df.columns:
                ip_counts = df['ip_location'].value_counts().head(10)
                plt.barh(range(len(ip_counts)), ip_counts.values)
                plt.yticks(range(len(ip_counts)), ip_counts.index)
                plt.title('视频发布地区Top10')
                plt.xlabel('视频数量')
            
            plt.tight_layout()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plt.savefig(f'{self.output_path}/content_analysis_{timestamp}.png', 
                       dpi=300, bbox_inches='tight')
            plt.close()
            
            utils.logger.info(f"[DouyinVisualStore] 已生成内容分析图表: content_analysis_{timestamp}.png")
            
        except Exception as e:
            utils.logger.error(f"[DouyinVisualStore] 生成内容图表失败: {e}")

    async def _generate_comment_charts(self):
        """生成评论相关图表"""
        try:
            pathlib.Path(self.output_path).mkdir(parents=True, exist_ok=True)
            
            if not self.data_cache['comments']:
                return
                
            df = pd.DataFrame(self.data_cache['comments'])
            
            # 创建大图表
            plt.figure(figsize=(16, 12))
            
            # 1. 评论点赞数分布
            plt.subplot(3, 3, 1)
            likes = pd.to_numeric(df['点赞数'], errors='coerce').fillna(0)
            plt.hist(likes, bins=30, alpha=0.7, color='orange')
            plt.title('评论点赞数分布')
            plt.xlabel('点赞数')
            plt.ylabel('评论数量')
            
            # 2. 评论时间分布（按小时）
            plt.subplot(3, 3, 2)
            if '评论时间' in df.columns:
                df['评论时间'] = pd.to_datetime(df['评论时间'])
                df['评论小时'] = df['评论时间'].dt.hour
                hourly_counts = df['评论小时'].value_counts().sort_index()
                plt.bar(hourly_counts.index, hourly_counts.values, alpha=0.7, color='lightcoral')
                plt.title('评论时间分布（按小时）')
                plt.xlabel('小时')
                plt.ylabel('评论数量')
            
            # 3. IP归属地分布
            plt.subplot(3, 3, 3)
            if 'ip归属' in df.columns and not df['ip归属'].isna().all():
                ip_counts = df['ip归属'].value_counts().head(10)
                plt.barh(range(len(ip_counts)), ip_counts.values)
                plt.yticks(range(len(ip_counts)), ip_counts.index)
                plt.title('评论地区分布Top10')
                plt.xlabel('评论数量')
            
            # 4. 作者回复率
            plt.subplot(3, 3, 4)
            if '作者已赞' in df.columns:
                author_reply = df['作者已赞'].value_counts()
                plt.pie(author_reply.values, labels=author_reply.index, autopct='%1.1f%%')
                plt.title('作者互动率')
            
            # 5. 评论长度分布
            plt.subplot(3, 3, 5)
            if '评论内容' in df.columns:
                content_lengths = df['评论内容'].astype(str).str.len()
                plt.hist(content_lengths, bins=30, alpha=0.7, color='lightblue')
                plt.title('评论长度分布')
                plt.xlabel('字符数')
                plt.ylabel('评论数量')
            
            # 6. 回复评论比例
            plt.subplot(3, 3, 6)
            if '父评论ID' in df.columns:
                reply_status = df['父评论ID'].apply(lambda x: '回复评论' if x != '0' and pd.notna(x) else '直接评论')
                reply_counts = reply_status.value_counts()
                plt.pie(reply_counts.values, labels=reply_counts.index, autopct='%1.1f%%')
                plt.title('评论类型分布')
            
            # 7. 评论词云
            plt.subplot(3, 3, 7)
            await self._generate_comment_wordcloud(df)
            
            # 8. 热门评论用户
            plt.subplot(3, 3, 8)
            if '用户昵称' in df.columns:
                top_users = df['用户昵称'].value_counts().head(10)
                plt.barh(range(len(top_users)), top_users.values)
                plt.yticks(range(len(top_users)), top_users.index)
                plt.title('最活跃评论用户Top10')
                plt.xlabel('评论数量')
            
            # 9. 评论情感词汇统计
            plt.subplot(3, 3, 9)
            await self._generate_sentiment_analysis(df)
            
            plt.tight_layout()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plt.savefig(f'{self.output_path}/comment_analysis_{timestamp}.png', 
                       dpi=300, bbox_inches='tight')
            plt.close()
            
            # 生成HTML报告
            await self._generate_html_report(df, timestamp)
            
            utils.logger.info(f"[DouyinVisualStore] 已生成评论分析图表: comment_analysis_{timestamp}.png")
            
        except Exception as e:
            utils.logger.error(f"[DouyinVisualStore] 生成评论图表失败: {e}")

    async def _generate_comment_wordcloud(self, df):
        """生成评论词云"""
        try:
            if '评论内容' not in df.columns:
                return
                
            # 合并所有评论内容
            all_comments = ' '.join(df['评论内容'].astype(str))
            
            # 清理文本
            all_comments = re.sub(r'[^\u4e00-\u9fa5\w\s]', '', all_comments)
            
            # 分词
            words = jieba.cut(all_comments)
            word_list = [word for word in words if len(word) > 1]
            
            if not word_list:
                plt.text(0.5, 0.5, '暂无足够的词汇数据', ha='center', va='center')
                plt.title('评论词云')
                return
            
            # 生成词云
            wordcloud = WordCloud(
                width=400, height=300,
                font_path='simhei.ttf',  # 可能需要调整字体路径
                background_color='white',
                max_words=100
            ).generate(' '.join(word_list))
            
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.title('评论词云')
            
        except Exception as e:
            plt.text(0.5, 0.5, f'词云生成失败: {str(e)}', ha='center', va='center')
            plt.title('评论词云')

    async def _generate_sentiment_analysis(self, df):
        """生成情感分析"""
        try:
            if '评论内容' not in df.columns:
                return
                
            # 简单的情感词汇统计
            positive_words = ['好', '棒', '赞', '喜欢', '爱', '支持', '优秀', '精彩']
            negative_words = ['差', '烂', '恶心', '讨厌', '垃圾', '无聊', '失望']
            
            positive_count = 0
            negative_count = 0
            
            for comment in df['评论内容'].astype(str):
                for word in positive_words:
                    positive_count += comment.count(word)
                for word in negative_words:
                    negative_count += comment.count(word)
            
            if positive_count + negative_count > 0:
                labels = ['积极词汇', '消极词汇']
                sizes = [positive_count, negative_count]
                colors = ['lightgreen', 'lightcoral']
                plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%')
                plt.title('评论情感词汇分布')
            else:
                plt.text(0.5, 0.5, '暂无情感词汇数据', ha='center', va='center')
                plt.title('评论情感词汇分布')
                
        except Exception as e:
            plt.text(0.5, 0.5, f'情感分析失败: {str(e)}', ha='center', va='center')
            plt.title('评论情感词汇分布')

    async def _generate_html_report(self, df, timestamp):
        """生成HTML可视化报告"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>抖音评论数据分析报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #007bff; border-left: 4px solid #007bff; padding-left: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .highlight {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }}
        .timestamp {{ text-align: center; color: #666; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 抖音评论数据分析报告</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(df)}</div>
                <div class="stat-label">总评论数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{df['用户昵称'].nunique() if '用户昵称' in df.columns else 0}</div>
                <div class="stat-label">参与用户数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{int(pd.to_numeric(df['点赞数'], errors='coerce').sum()) if '点赞数' in df.columns else 0}</div>
                <div class="stat-label">总点赞数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{df['ip归属'].nunique() if 'ip归属' in df.columns else 0}</div>
                <div class="stat-label">地区分布</div>
            </div>
        </div>

        <h2>🔥 热门评论Top10</h2>
        <table>
            <tr><th>用户昵称</th><th>评论内容</th><th>点赞数</th><th>评论时间</th></tr>
"""
            
            # 添加热门评论
            if '点赞数' in df.columns and '评论内容' in df.columns:
                top_comments = df.nlargest(10, '点赞数')
                for _, comment in top_comments.iterrows():
                    content = str(comment.get('评论内容', ''))[:50] + '...' if len(str(comment.get('评论内容', ''))) > 50 else str(comment.get('评论内容', ''))
                    html_content += f"""
            <tr>
                <td>{comment.get('用户昵称', 'N/A')}</td>
                <td>{content}</td>
                <td>{comment.get('点赞数', 0)}</td>
                <td>{comment.get('评论时间', 'N/A')}</td>
            </tr>"""

            html_content += f"""
        </table>

        <h2>👥 活跃用户Top10</h2>
        <table>
            <tr><th>用户昵称</th><th>评论数量</th><th>平均点赞数</th></tr>
"""
            
            # 添加活跃用户
            if '用户昵称' in df.columns:
                user_stats = df.groupby('用户昵称').agg({
                    '评论内容': 'count',
                    '点赞数': lambda x: pd.to_numeric(x, errors='coerce').mean()
                }).sort_values('评论内容', ascending=False).head(10)
                
                for user, stats in user_stats.iterrows():
                    html_content += f"""
            <tr>
                <td>{user}</td>
                <td>{stats['评论内容']}</td>
                <td>{stats['点赞数']:.1f}</td>
            </tr>"""

            html_content += f"""
        </table>

        <div class="highlight">
            💡 <strong>数据洞察：</strong>
            <ul>
                <li>评论参与度较高的时间段建议关注</li>
                <li>高点赞评论可作为内容优化参考</li>
                <li>活跃用户群体值得深度运营</li>
            </ul>
        </div>

        <div class="timestamp">
            📅 报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

            # 保存HTML文件
            html_file = f'{self.output_path}/report_{timestamp}.html'
            async with aiofiles.open(html_file, 'w', encoding='utf-8') as f:
                await f.write(html_content)
                
            utils.logger.info(f"[DouyinVisualStore] 已生成HTML报告: report_{timestamp}.html")
            
        except Exception as e:
            utils.logger.error(f"[DouyinVisualStore] 生成HTML报告失败: {e}")

    async def generate_final_report(self):
        """生成最终完整报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 生成完整的统计图表
            if self.data_cache['comments']:
                await self._generate_comment_charts()
            
            # 保存数据到JSON
            data_file = f'{self.output_path}/complete_data_{timestamp}.json'
            async with aiofiles.open(data_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.data_cache, ensure_ascii=False, indent=2))
            
            utils.logger.info(f"[DouyinVisualStore] 最终报告已生成完成！")
            utils.logger.info(f"[DouyinVisualStore] 图表文件: {self.output_path}/comment_analysis_{timestamp}.png")
            utils.logger.info(f"[DouyinVisualStore] HTML报告: {self.output_path}/report_{timestamp}.html")
            utils.logger.info(f"[DouyinVisualStore] 数据文件: {data_file}")
            
        except Exception as e:
            utils.logger.error(f"[DouyinVisualStore] 生成最终报告失败: {e}")