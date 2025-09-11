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
抖音数据实时Web可视化界面
使用方法: 
1. 设置 SAVE_DATA_OPTION = "web" 
2. 运行爬虫程序
3. 浏览器访问 http://localhost:8081 查看实时数据
"""

import asyncio
import json
import os
import re
from typing import Dict, List
from datetime import datetime, timedelta
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import urllib.parse
from collections import Counter
import jieba
import wordcloud
from io import BytesIO
import base64

from base.base_crawler import AbstractStore
from tools import utils


class DouyinWebStoreImplement(AbstractStore):
    """抖音Web实时可视化存储实现类"""
    
    def __init__(self):
        self.web_path = "data/douyin/web"
        self.data_cache = {
            'contents': [],
            'comments': [],
            'creators': [],
            'stats': {
                'total_comments': 0,
                'total_users': 0,
                'total_likes': 0,
                'avg_likes': 0,
                'reply_ratio': 0,
                'author_liked_count': 0,
                'last_update': ''
            },
            'analytics': {
                'hourly_distribution': {},
                'likes_distribution': {},
                'location_distribution': {},
                'word_cloud': '',
                'sentiment_analysis': {},
                'top_users': [],
                'recent_comments': []
            }
        }
        self.lock = asyncio.Lock()
        self._server_started = False
        self._update_count = 0
        
    async def bulk_import_comments(self, comments: List[Dict], analyze_after: bool = True):
        """批量导入评论：一次性追加并统一更新统计/分析，避免逐条I/O和计算"""
        if not comments:
            return
        async with self.lock:
            # 确保Web服务已启动
            if not self._server_started:
                await self._start_web_server()
                self._server_started = True
                
            # 规范化与追加
            for c in comments:
                try:
                    # 保障必要字段存在与类型
                    c.setdefault('评论时间', c.get('评论时间', ''))
                    c.setdefault('用户昵称', c.get('用户昵称', ''))
                    c.setdefault('评论内容', c.get('评论内容', ''))
                    # 点赞数尽量转为int
                    digg = c.get('点赞数', 0)
                    try:
                        c['点赞数'] = int(digg)
                    except Exception:
                        c['点赞数'] = 0
                    c.setdefault('被回复人昵称', c.get('被回复人昵称', ''))
                    c.setdefault('作者已赞', c.get('作者已赞', ''))
                    c.setdefault('ip归属', c.get('ip归属', ''))
                    c.setdefault('评论图片', c.get('评论图片', ''))
                except Exception:
                    pass
                    
            # 添加到缓存
            self.data_cache['comments'].extend(comments)
            
            # 按时间排序（最新的在前面）
            self.data_cache['comments'].sort(key=lambda x: self._parse_comment_time(x.get('评论时间', '')), reverse=True)
            
            utils.logger.info(f"[DouyinWebStore] 已添加 {len(comments)} 条评论到缓存，总数: {len(self.data_cache['comments'])}")
            
            # 统一更新统计
            await self._update_statistics()
            
            # 强制更新Web数据文件
            await self._update_web_data()

    async def store_content(self, content_item: Dict):
        """存储内容"""
        async with self.lock:
            self.data_cache['contents'].append(content_item)
            await self._update_web_data()

    async def store_comment(self, comment_item: Dict):
        """存储评论并更新Web页面"""
        async with self.lock:
            self.data_cache['comments'].append(comment_item)
            self._update_count += 1
            
            # 更新统计信息
            await self._update_statistics()
            
            # 启动Web服务器（仅启动一次）
            if not self._server_started:
                await self._start_web_server()
                self._server_started = True
            
            # 每5条评论更新一次Web数据（更频繁的更新）
            if self._update_count % 5 == 0:
                await self._update_web_data()

    async def store_creator(self, creator: Dict):
        """存储创作者信息"""
        async with self.lock:
            self.data_cache['creators'].append(creator)
            await self._update_web_data()

    async def _update_statistics(self):
        """更新统计信息和分析数据"""
        comments = self.data_cache['comments']
        if not comments:
            return
            
        # 基础统计
        self.data_cache['stats']['total_comments'] = len(comments)
        self.data_cache['stats']['total_users'] = len(set(c.get('用户昵称', '') for c in comments))
        self.data_cache['stats']['total_likes'] = sum(int(c.get('点赞数', 0)) for c in comments)
        self.data_cache['stats']['avg_likes'] = round(self.data_cache['stats']['total_likes'] / max(1, self.data_cache['stats']['total_comments']), 2)
        self.data_cache['stats']['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 回复比例
        reply_count = sum(1 for c in comments if c.get('被回复人昵称', ''))
        self.data_cache['stats']['reply_ratio'] = round(reply_count / max(1, len(comments)) * 100, 2)
        
        # 作者点赞数
        author_liked_count = sum(1 for c in comments if c.get('作者已赞', '') == '是')
        self.data_cache['stats']['author_liked_count'] = author_liked_count
        
        # 分析数据
        await self._update_analytics()

    def _parse_comment_time(self, time_str):
        """解析评论时间字符串为datetime对象"""
        try:
            if not time_str:
                return datetime.min
            # 尝试解析时间字符串
            return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                # 尝试其他时间格式
                return datetime.strptime(time_str, '%Y-%m-%d')
            except:
                return datetime.min

    async def _update_analytics(self):
        """更新分析数据"""
        comments = self.data_cache['comments']
        if not comments:
            return
            
        # 时间分布分析
        hourly_dist = {}
        for comment in comments:
            try:
                comment_time = datetime.strptime(comment.get('评论时间', ''), '%Y-%m-%d %H:%M:%S')
                hour = comment_time.hour
                hourly_dist[hour] = hourly_dist.get(hour, 0) + 1
            except:
                continue
        self.data_cache['analytics']['hourly_distribution'] = hourly_dist
        
        # 点赞数分布
        likes_dist = {'0-10': 0, '11-50': 0, '51-100': 0, '101-500': 0, '500+': 0}
        for comment in comments:
            likes = int(comment.get('点赞数', 0))
            if likes <= 10:
                likes_dist['0-10'] += 1
            elif likes <= 50:
                likes_dist['11-50'] += 1
            elif likes <= 100:
                likes_dist['51-100'] += 1
            elif likes <= 500:
                likes_dist['101-500'] += 1
            else:
                likes_dist['500+'] += 1
        self.data_cache['analytics']['likes_distribution'] = likes_dist
        
        # 地理位置分布
        location_dist = Counter()
        for comment in comments:
            location = comment.get('ip归属', '未知')
            if location and location != '未知':
                location_dist[location] += 1
        self.data_cache['analytics']['location_distribution'] = dict(location_dist.most_common(10))
        
        # 词云分析
        await self._generate_word_cloud()
        
        # 情感分析
        await self._analyze_sentiment()
        
        # 活跃用户排行
        user_activity = Counter()
        for comment in comments:
            user = comment.get('用户昵称', '')
            if user:
                user_activity[user] += 1
        self.data_cache['analytics']['top_users'] = [{'user': user, 'count': count} for user, count in user_activity.most_common(10)]
        
        # 最新评论
        recent_comments = sorted(comments, key=lambda x: self._parse_comment_time(x.get('评论时间', '')), reverse=True)[:20]
        self.data_cache['analytics']['recent_comments'] = recent_comments

    async def _generate_word_cloud(self):
        """生成词云"""
        try:
            comments = self.data_cache['comments']
            if not comments:
                return
                
            # 提取评论内容
            texts = []
            for comment in comments:
                content = comment.get('评论内容', '')
                if content:
                    # 清理文本
                    content = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', content)
                    texts.append(content)
            
            if not texts:
                return
                
            # 分词
            all_text = ' '.join(texts)
            words = jieba.cut(all_text)
            word_list = [word for word in words if len(word) > 1 and word not in ['的', '了', '是', '在', '有', '和', '就', '都', '而', '及', '与', '或', '但', '因为', '所以', '如果', '虽然', '但是', '然后', '而且', '还是', '就是', '这个', '那个', '什么', '怎么', '为什么', '哪里', '什么时候', '多少', '几个', '一些', '很多', '非常', '特别', '很', '太', '更', '最', '比较', '相当', '十分', '极其', '完全', '绝对', '确实', '真的', '确实', '当然', '肯定', '一定', '必须', '应该', '需要', '想要', '希望', '喜欢', '爱', '讨厌', '不喜欢', '觉得', '认为', '感觉', '知道', '了解', '明白', '理解', '记得', '忘记', '想起', '想到', '看到', '听到', '闻到', '尝到', '摸到', '感到', '觉得', '认为', '感觉', '知道', '了解', '明白', '理解', '记得', '忘记', '想起', '想到', '看到', '听到', '闻到', '尝到', '摸到', '感到']]
            
            # 统计词频
            word_freq = Counter(word_list)
            
            # 生成词云
            if word_freq:
                wc = wordcloud.WordCloud(
                    font_path='C:/Windows/Fonts/simhei.ttf',  # Windows中文字体
                    width=400,
                    height=300,
                    background_color='white',
                    max_words=50,
                    colormap='viridis'
                ).generate_from_frequencies(word_freq)
                
                # 转换为base64
                img_buffer = BytesIO()
                wc.to_image().save(img_buffer, format='PNG')
                img_str = base64.b64encode(img_buffer.getvalue()).decode()
                self.data_cache['analytics']['word_cloud'] = f"data:image/png;base64,{img_str}"
                
        except Exception as e:
            utils.logger.error(f"[DouyinWebStore] 生成词云失败: {e}")

    async def _analyze_sentiment(self):
        """简单情感分析"""
        try:
            comments = self.data_cache['comments']
            if not comments:
                return
                
            positive_words = ['好', '棒', '赞', '喜欢', '爱', '美', '棒棒', '优秀', '完美', '太棒了', '厉害', '牛', '强', '赞赞', '666', '支持', '加油', '棒极了', '太棒', '超级', '非常', '特别', '真的', '确实', '当然', '肯定', '绝对', '完全', '十分', '极其', '相当', '比较', '更', '最', '太', '很', '非常', '特别', '真的', '确实', '当然', '肯定', '绝对', '完全', '十分', '极其', '相当', '比较', '更', '最', '太', '很']
            negative_words = ['差', '烂', '讨厌', '不喜欢', '恶心', '垃圾', '糟糕', '坏', '烂透了', '太差', '不行', '不好', '难看', '丑', '无聊', '没意思', '失望', '生气', '愤怒', '讨厌', '恨', '恶心', '垃圾', '糟糕', '坏', '烂透了', '太差', '不行', '不好', '难看', '丑', '无聊', '没意思', '失望', '生气', '愤怒', '讨厌', '恨']
            
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
            
            for comment in comments:
                content = comment.get('评论内容', '')
                if not content:
                    continue
                    
                positive_score = sum(1 for word in positive_words if word in content)
                negative_score = sum(1 for word in negative_words if word in content)
                
                if positive_score > negative_score:
                    sentiment_counts['positive'] += 1
                elif negative_score > positive_score:
                    sentiment_counts['negative'] += 1
                else:
                    sentiment_counts['neutral'] += 1
            
            self.data_cache['analytics']['sentiment_analysis'] = sentiment_counts
            
        except Exception as e:
            utils.logger.error(f"[DouyinWebStore] 情感分析失败: {e}")

    async def _start_web_server(self):
        """启动Web服务器"""
        try:
            # 创建Web目录和文件
            os.makedirs(self.web_path, exist_ok=True)
            await self._create_web_files()
            
            # 在后台线程启动HTTP服务器
            def start_server():
                try:
                    os.chdir(self.web_path)
                    handler = self._create_request_handler()
                    # 尝试使用8082端口，如果被占用则使用8083
                    port = 8082
                    try:
                        with socketserver.TCPServer(("", port), handler) as httpd:
                            utils.logger.info(f"[DouyinWebStore] Web服务器已启动: http://localhost:{port}")
                            # 自动打开浏览器
                            threading.Timer(2, lambda: webbrowser.open(f'http://localhost:{port}')).start()
                            httpd.serve_forever()
                    except OSError as e:
                        if "Address already in use" in str(e):
                            port = 8083
                            utils.logger.info(f"[DouyinWebStore] 端口8082被占用，尝试使用端口{port}")
                            with socketserver.TCPServer(("", port), handler) as httpd:
                                utils.logger.info(f"[DouyinWebStore] Web服务器已启动: http://localhost:{port}")
                                # 自动打开浏览器
                                threading.Timer(2, lambda: webbrowser.open(f'http://localhost:{port}')).start()
                                httpd.serve_forever()
                        else:
                            raise e
                except Exception as e:
                    utils.logger.error(f"[DouyinWebStore] Web服务器启动失败: {e}")
            
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            
        except Exception as e:
            utils.logger.error(f"[DouyinWebStore] 启动Web服务器失败: {e}")

    def _create_request_handler(self):
        """创建自定义HTTP请求处理器"""
        web_store = self
        
        class CustomHTTPRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    if self.path == '/data.json':
                        self._serve_data()
                    elif self.path.startswith('/api/comments'):
                        self._serve_comments_api()
                    elif self.path.startswith('/api/author-liked'):
                        self._serve_author_liked_api()
                    elif self.path.startswith('/export/'):
                        self._serve_export()
                    else:
                        self._serve_static()
                except Exception as e:
                    self._send_error_response(500, str(e))
            
            def _serve_data(self):
                """提供数据API"""
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                # 获取最新数据
                data = web_store.data_cache.copy()
                self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
            
            def _serve_comments_api(self):
                """提供分页评论API"""
                parsed_url = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                page = int(query_params.get('page', [1])[0])
                per_page = 12  # 改为12条评论，适合三列布局（4行 x 3列）
                
                comments = web_store.data_cache.get('comments', [])
                # 按时间倒序排列（最新的在前面）
                sorted_comments = sorted(comments, key=lambda x: self._parse_comment_time(x.get('评论时间', '')), reverse=True)
                
                # 分页处理
                total = len(sorted_comments)
                start = (page - 1) * per_page
                end = start + per_page
                page_comments = sorted_comments[start:end]
                
                response_data = {
                    'comments': page_comments,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': (total + per_page - 1) // per_page,
                        'has_next': end < total,
                        'has_prev': page > 1
                    }
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False, indent=2).encode('utf-8'))
            
            def _parse_comment_time(self, time_str):
                """解析评论时间字符串为datetime对象"""
                try:
                    if not time_str:
                        return datetime.min
                    # 尝试解析时间字符串
                    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        # 尝试其他时间格式
                        return datetime.strptime(time_str, '%Y-%m-%d')
                    except:
                        return datetime.min
            
            def _serve_author_liked_api(self):
                """提供作者赞过的评论API"""
                parsed_url = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                page = int(query_params.get('page', [1])[0])
                per_page = 12  # 改为12条评论，适合三列布局
                
                comments = web_store.data_cache.get('comments', [])
                # 筛选作者赞过的评论
                author_liked_comments = [c for c in comments if c.get('作者已赞', '') == '是']
                # 按时间倒序排列（最新的在前面）
                sorted_comments = sorted(author_liked_comments, key=lambda x: self._parse_comment_time(x.get('评论时间', '')), reverse=True)
                
                # 分页处理
                total = len(sorted_comments)
                start = (page - 1) * per_page
                end = start + per_page
                page_comments = sorted_comments[start:end]
                
                response_data = {
                    'comments': page_comments,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': (total + per_page - 1) // per_page,
                        'has_next': end < total,
                        'has_prev': page > 1
                    }
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False, indent=2).encode('utf-8'))
            
            def _serve_export(self):
                """提供数据导出功能"""
                export_type = self.path.split('/')[-1]
                
                if export_type == 'csv':
                    self._export_csv()
                elif export_type == 'excel':
                    self._export_excel()
                else:
                    self._send_error_response(404, "不支持的导出格式")
            
            def _export_csv(self):
                """导出CSV文件"""
                try:
                    import csv
                    import io
                    
                    comments = web_store.data_cache.get('comments', [])
                    if not comments:
                        self._send_error_response(404, "没有数据可导出")
                        return
                    
                    # 创建CSV内容
                    output = io.StringIO()
                    if comments:
                        fieldnames = list(comments[0].keys())
                        writer = csv.DictWriter(output, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(comments)
                    
                    csv_content = output.getvalue()
                    output.close()
                    
                    # 发送文件
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/csv; charset=utf-8')
                    self.send_header('Content-Disposition', 'attachment; filename="douyin_comments.csv"')
                    self.end_headers()
                    self.wfile.write(csv_content.encode('utf-8-sig'))
                    
                except Exception as e:
                    self._send_error_response(500, f"CSV导出失败: {str(e)}")
            
            def _export_excel(self):
                """导出Excel文件"""
                try:
                    import pandas as pd
                    import io
                    
                    comments = web_store.data_cache.get('comments', [])
                    if not comments:
                        self._send_error_response(404, "没有数据可导出")
                        return
                    
                    # 创建DataFrame
                    df = pd.DataFrame(comments)
                    
                    # 创建Excel内容
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='评论数据', index=False)
                    
                    excel_content = output.getvalue()
                    output.close()
                    
                    # 发送文件
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    self.send_header('Content-Disposition', 'attachment; filename="douyin_comments.xlsx"')
                    self.end_headers()
                    self.wfile.write(excel_content)
                    
                except Exception as e:
                    self._send_error_response(500, f"Excel导出失败: {str(e)}")
            
            def _serve_static(self):
                """提供静态文件"""
                if self.path == '/':
                    self.path = '/index.html'
                
                try:
                    with open(self.path[1:], 'rb') as f:
                        content = f.read()
                    
                    self.send_response(200)
                    if self.path.endswith('.html'):
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                    elif self.path.endswith('.js'):
                        self.send_header('Content-Type', 'application/javascript')
                    elif self.path.endswith('.css'):
                        self.send_header('Content-Type', 'text/css')
                    else:
                        self.send_header('Content-Type', 'application/octet-stream')
                    self.end_headers()
                    self.wfile.write(content)
                    
                except FileNotFoundError:
                    self._send_error_response(404, "文件未找到")
            
            def _send_error_response(self, code, message):
                """发送错误响应"""
                self.send_response(code)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head><title>错误 {code}</title></head>
                <body>
                    <h1>错误 {code}</h1>
                    <p>{message}</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode('utf-8'))
            
            def log_message(self, format, *args):
                """禁用默认日志"""
                pass
        
        return CustomHTTPRequestHandler

    async def _create_web_files(self):
        """创建Web页面文件"""
        # 创建主页面HTML
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>抖音评论数据实时监控仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .header { 
            background: rgba(255, 255, 255, 0.1); 
            backdrop-filter: blur(10px);
            color: white; 
            padding: 20px; 
            text-align: center; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .container { max-width: 1400px; margin: 20px auto; padding: 0 20px; }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .stat-card { 
            background: rgba(255, 255, 255, 0.95); 
            padding: 25px; 
            border-radius: 15px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .stat-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 12px 40px rgba(0,0,0,0.15);
        }
        .stat-icon { font-size: 2.5em; margin-bottom: 10px; }
        .stat-number { font-size: 2.2em; font-weight: bold; color: #667eea; margin-bottom: 5px; }
        .stat-label { color: #666; font-size: 0.9em; }
        .charts-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .chart-card { 
            background: rgba(255, 255, 255, 0.95); 
            padding: 25px; 
            border-radius: 15px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .chart-title { 
            font-size: 1.3em; 
            font-weight: bold; 
            margin-bottom: 20px; 
            color: #333; 
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .comments-section { 
            background: rgba(255, 255, 255, 0.95); 
            padding: 25px; 
            border-radius: 15px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .section-title { font-size: 1.5em; font-weight: bold; color: #333; }
        .btn-group { display: flex; gap: 10px; flex-wrap: wrap; }
        .btn { 
            background: #667eea; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 0.9em;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .btn:hover { 
            background: #5a6fd8; 
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #5a6268; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .comment-item { 
            border: 1px solid #e0e0e0; 
            border-radius: 12px;
            padding: 15px; 
            margin: 10px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            height: auto;
            min-height: 180px;
        }
        .comment-item:hover { 
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        /* 展开按钮样式 */
        .expand-btn {
            color: #667eea;
            cursor: pointer;
            font-weight: bold;
            margin-left: 5px;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.85em;
            transition: all 0.3s ease;
        }
        .expand-btn:hover {
            background-color: #667eea;
            color: white;
        }
        
        /* 回复指示器样式 */
        .reply-indicator {
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        .reply-indicator:hover {
            background-color: #f0f4ff;
            color: #667eea;
        }
        
        /* 弹窗样式 */
        .reply-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-content {
            background: white;
            border-radius: 15px;
            width: 80%;
            max-width: 600px;
            max-height: 80%;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .modal-header {
            padding: 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .modal-header h3 {
            margin: 0;
            font-size: 1.3em;
        }
        
        .close-btn {
            font-size: 24px;
            cursor: pointer;
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 50%;
            transition: background-color 0.3s ease;
        }
        .close-btn:hover {
            background-color: rgba(255,255,255,0.2);
        }
        
        .modal-body {
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .reply-item {
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid;
        }
        
        .reply-item.is-original {
            background-color: #f8f9ff;
            border-left-color: #667eea;
        }
        
        .reply-item.is-reply {
            background-color: #fff8f0;
            border-left-color: #ff9500;
            margin-left: 20px;
        }
        
        .reply-user {
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }
        
        .reply-to {
            color: #ff9500;
            font-size: 0.9em;
        }
        
        .original-comment {
            color: #667eea;
            font-size: 0.9em;
        }
        
        .reply-content {
            margin-bottom: 10px;
            line-height: 1.5;
            color: #555;
        }
        
        .reply-meta {
            font-size: 0.85em;
            color: #999;
        }
        
        .reply-meta span {
            margin-right: 15px;
        }
        
        /* 暂无回复样式 */
        .no-replies {
            text-align: center;
            color: #999;
            font-style: italic;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
            margin-top: 10px;
        }
        .comment-user { 
            font-weight: bold; 
            color: #667eea; 
            margin-bottom: 8px; 
            font-size: 1.1em;
        }
        .comment-content { 
            margin-bottom: 10px; 
            line-height: 1.6; 
            font-size: 1em;
        }
        
        /* 评论图片样式 */
        .comment-images {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }
        .comment-image-wrapper {
            position: relative;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        .comment-image-wrapper:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .comment-image {
            width: 60px;
            height: 60px;
            object-fit: cover;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        .comment-image:hover {
            opacity: 0.8;
        }
        
        /* 图片模态窗口样式 */
        .image-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 2000;
            backdrop-filter: blur(5px);
        }
        .image-modal img {
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }
        .image-modal .close-btn {
            position: absolute;
            top: 20px;
            right: 30px;
            color: white;
            font-size: 35px;
            cursor: pointer;
            background: rgba(0,0,0,0.5);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        .image-modal .close-btn:hover {
            background: rgba(255,255,255,0.2);
            transform: scale(1.1);
        }
        .comment-meta { 
            font-size: 0.85em; 
            color: #666; 
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }
        .meta-item { display: flex; align-items: center; gap: 5px; }
        .status { 
            text-align: center; 
            margin: 20px 0; 
            color: #666; 
            font-style: italic;
        }
        .loading { 
            display: inline-block; 
            width: 20px; 
            height: 20px; 
            border: 3px solid #f3f3f3; 
            border-top: 3px solid #667eea; 
            border-radius: 50%; 
            animation: spin 1s linear infinite; 
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .word-cloud-container { text-align: center; margin: 20px 0; }
        .word-cloud-img { max-width: 100%; height: auto; border-radius: 10px; }
        .tabs { 
            display: flex; 
            margin-bottom: 20px; 
            border-bottom: 2px solid #eee; 
        }
        .tab { 
            padding: 10px 20px; 
            cursor: pointer; 
            border-bottom: 3px solid transparent; 
            transition: all 0.3s ease;
        }
        .tab.active { 
            color: #667eea; 
            border-bottom-color: #667eea; 
            font-weight: bold;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .user-list { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
            gap: 15px; 
        }
        .user-item { 
            background: #f8f9fa; 
            padding: 15px; 
            border-radius: 10px; 
            text-align: center;
        }
        .user-name { font-weight: bold; color: #333; margin-bottom: 5px; }
        .user-count { color: #667eea; font-size: 1.2em; }
        .sentiment-chart { max-height: 300px; }
        .location-list { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); 
            gap: 10px; 
        }
        .location-item { 
            background: #f8f9fa; 
            padding: 10px; 
            border-radius: 8px; 
            text-align: center;
        }
        .location-name { font-weight: bold; margin-bottom: 5px; }
        .location-count { color: #667eea; }
        .responsive-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
        }
        
        /* 分页样式 */
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin: 30px 0;
            flex-wrap: wrap;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        .pagination-btn {
            background: linear-gradient(145deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: all 0.3s ease;
            min-width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            position: relative;
            overflow: hidden;
        }
        .pagination-btn:hover {
            background: linear-gradient(145deg, #5a6fd8, #6a4190);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        .pagination-btn:active {
            transform: translateY(0);
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
        }
        .pagination-btn:disabled {
            background: #e0e0e0;
            color: #999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .pagination-btn.active {
            background: linear-gradient(145deg, #28a745, #20c997);
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
        }
        .pagination-btn.active:hover {
            background: linear-gradient(145deg, #218838, #1ea486);
        }
        .pagination-info {
            background: rgba(255, 255, 255, 0.9);
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.85em;
            color: #333;
            font-weight: 500;
            margin: 0 5px;
            backdrop-filter: blur(5px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        /* 分页按钮图标样式 */
        .pagination-btn i {
            margin: 0 4px;
        }
        /* 省略号样式 */
        .pagination-info:not(:last-child) {
            color: #666;
            font-weight: bold;
        }
        
        /* 搜索功能样式 */
        .search-container {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-left: 15px;
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
            backdrop-filter: blur(5px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .search-input {
            border: none;
            background: transparent;
            padding: 6px 10px;
            font-size: 0.85em;
            outline: none;
            color: #333;
            min-width: 120px;
        }
        .search-input::placeholder {
            color: #999;
        }
        .search-btn {
            background: linear-gradient(145deg, #17a2b8, #138496);
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .search-btn:hover {
            background: linear-gradient(145deg, #138496, #117a8b);
            transform: translateY(-1px);
        }
        .clear-btn {
            background: linear-gradient(145deg, #6c757d, #5a6268);
            color: white;
            border: none;
            padding: 6px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.3s ease;
        }
        .clear-btn:hover {
            background: linear-gradient(145deg, #5a6268, #495057);
            transform: translateY(-1px);
        }
        /* 评论网格布局 */
        .comments-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        
        /* 响应式设计 */
        @media (max-width: 1200px) {
            .comments-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .comments-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-chart-line"></i> 抖音评论数据实时监控仪表板</h1>
        <p>实时展示评论数据分析结果 - 数据驱动洞察</p>
    </div>
    
    <div class="container">
        <!-- 统计卡片 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <div class="stat-number" id="total-comments">0</div>
                <div class="stat-label">总评论数</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-number" id="total-users">0</div>
                <div class="stat-label">参与用户</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">👍</div>
                <div class="stat-number" id="total-likes">0</div>
                <div class="stat-label">总点赞数</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-number" id="avg-likes">0</div>
                <div class="stat-label">平均点赞数</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <div class="stat-number" id="reply-ratio">0%</div>
                <div class="stat-label">回复比例</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">❤️</div>
                <div class="stat-number" id="author-liked">0</div>
                <div class="stat-label">作者点赞数</div>
            </div>
        </div>
        
        <!-- 图表区域 -->
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">
                    <i class="fas fa-clock"></i> 评论时间分布
                </div>
                <canvas id="timeChart" width="400" height="200"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">
                    <i class="fas fa-heart"></i> 点赞数分布
                </div>
                <canvas id="likesChart" width="400" height="200"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">
                    <i class="fas fa-smile"></i> 情感分析
                </div>
                <canvas id="sentimentChart" width="400" height="200"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">
                    <i class="fas fa-map-marker-alt"></i> 地理位置分布
                </div>
                <div id="locationChart"></div>
            </div>
        </div>
        
        <!-- 词云图 -->
        <div class="chart-card">
            <div class="chart-title">
                <i class="fas fa-cloud"></i> 评论词云
            </div>
            <div class="word-cloud-container" id="wordCloudContainer">
                <div class="status">正在生成词云...</div>
            </div>
        </div>
        
        <!-- 标签页内容 -->
        <div class="comments-section">
            <div class="section-header">
                <div class="section-title">数据分析</div>
                <div class="btn-group">
                    <button class="btn" onclick="loadData()">
                        <i class="fas fa-sync-alt"></i> 刷新数据
                    </button>
                    <button class="btn btn-secondary" onclick="exportData('csv')">
                        <i class="fas fa-download"></i> 导出CSV
                    </button>
                    <button class="btn btn-success" onclick="exportData('excel')">
                        <i class="fas fa-file-excel"></i> 导出Excel
                    </button>
                </div>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="switchTab('comments')">最新评论</div>
                <div class="tab" onclick="switchTab('users')">活跃用户</div>
                <div class="tab" onclick="switchTab('locations')">地区分布</div>
                <div class="tab" onclick="switchTab('author-liked')">作者已赞</div>
            </div>
            
            <div class="tab-content active" id="comments-tab">
                <div class="status" id="status">正在加载数据...</div>
                <div id="comments-list"></div>
                <div class="pagination" id="comments-pagination"></div>
            </div>
            
            <div class="tab-content" id="users-tab">
                <div id="users-list"></div>
            </div>
            
            <div class="tab-content" id="locations-tab">
                <div id="locations-list"></div>
            </div>
            
            <div class="tab-content" id="author-liked-tab">
                <div class="status" id="author-liked-status">正在加载数据...</div>
                <div id="author-liked-list"></div>
                <div class="pagination" id="author-liked-pagination"></div>
            </div>
        </div>
    </div>

    <script>
        let timeChart, likesChart, sentimentChart;
        let currentData = null;
        let allComments = []; // 存储所有评论数据
        let filteredComments = []; // 存储过滤后的评论数据
        let authorLikedComments = []; // 存储作者已赞的评论
        let currentPage = 1; // 当前页码
        let commentsPerPage = 12; // 改为12条评论，适合三列布局
        let currentSearchQuery = ''; // 当前搜索关键词
        
        // 作者已赞评论的分页变量
        let authorLikedCurrentPage = 1;
        let authorLikedSearchQuery = '';
        
        // 初始化图表
        function initCharts() {
            // 时间分布图表
            const timeCtx = document.getElementById('timeChart').getContext('2d');
            timeChart = new Chart(timeCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: '评论数量',
                        data: [],
                        backgroundColor: 'rgba(102, 126, 234, 0.6)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
            
            // 点赞分布图表
            const likesCtx = document.getElementById('likesChart').getContext('2d');
            likesChart = new Chart(likesCtx, {
                type: 'doughnut',
                data: {
                    labels: ['0-10赞', '11-50赞', '51-100赞', '101-500赞', '500+赞'],
                    datasets: [{
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.6)',
                            'rgba(54, 162, 235, 0.6)',
                            'rgba(255, 205, 86, 0.6)',
                            'rgba(75, 192, 192, 0.6)',
                            'rgba(153, 102, 255, 0.6)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
            
            // 情感分析图表
            const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
            sentimentChart = new Chart(sentimentCtx, {
                type: 'pie',
                data: {
                    labels: ['正面', '负面', '中性'],
                    datasets: [{
                        data: [0, 0, 0],
                        backgroundColor: [
                            'rgba(40, 167, 69, 0.6)',
                            'rgba(220, 53, 69, 0.6)',
                            'rgba(108, 117, 125, 0.6)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
        
        // 加载数据
        async function loadData() {
            try {
                document.getElementById('status').innerHTML = '<div class="loading"></div> 正在加载数据...';
                
                const response = await fetch('/data.json');
                const data = await response.json();
                currentData = data;
                
                // 存储所有评论数据用于分页，并按时间排序（最新的在前）
                allComments = (data.comments || []).sort((a, b) => {
                    const timeA = parseCommentTime(a['评论时间'] || '');
                    const timeB = parseCommentTime(b['评论时间'] || '');
                    return timeB - timeA; // 降序排列，最新的在前
                });
                console.log('加载评论数据:', allComments.length, '条');
                
                // 筛选作者已赞的评论
                authorLikedComments = allComments.filter(comment => 
                    comment['作者已赞'] === '是'
                ).sort((a, b) => {
                    const timeA = parseCommentTime(a['评论时间'] || '');
                    const timeB = parseCommentTime(b['评论时间'] || '');
                    return timeB - timeA; // 降序排列，最新的在前
                });
                console.log('作者已赞评论数据:', authorLikedComments.length, '条');
                
                // 更新统计卡片
                updateStats(data.stats);
                
                // 更新图表
                updateCharts(data);
                
                // 显示第一页评论
                displayCommentsPage(1);
                
                // 更新用户列表
                updateUsersList(data.analytics.top_users || []);
                
                // 更新地区列表
                updateLocationsList(data.analytics.location_distribution || {});
                
                // 更新词云
                updateWordCloud(data.analytics.word_cloud);
                
            } catch (error) {
                document.getElementById('status').textContent = '数据加载失败，请确保爬虫正在运行';
                console.error('Error loading data:', error);
            }
        }
        
        // 更新统计信息
        function updateStats(stats) {
            document.getElementById('total-comments').textContent = stats.total_comments || 0;
            document.getElementById('total-users').textContent = stats.total_users || 0;
            document.getElementById('total-likes').textContent = stats.total_likes || 0;
            document.getElementById('avg-likes').textContent = stats.avg_likes || 0;
            document.getElementById('reply-ratio').textContent = (stats.reply_ratio || 0) + '%';
            document.getElementById('author-liked').textContent = stats.author_liked_count || 0;
        }
        
        // 更新图表
        function updateCharts(data) {
            const comments = data.comments || [];
            const analytics = data.analytics || {};
            
            if (comments.length === 0) return;
            
            // 更新时间分布图表
            const hourlyDist = analytics.hourly_distribution || {};
            const timeLabels = Object.keys(hourlyDist).sort((a, b) => a - b).map(h => h + ':00');
            const timeData = Object.keys(hourlyDist).sort((a, b) => a - b).map(h => hourlyDist[h]);
            
            timeChart.data.labels = timeLabels;
            timeChart.data.datasets[0].data = timeData;
            timeChart.update();
            
            // 更新点赞分布图表
            const likesDist = analytics.likes_distribution || {};
            likesChart.data.datasets[0].data = [
                likesDist['0-10'] || 0,
                likesDist['11-50'] || 0,
                likesDist['51-100'] || 0,
                likesDist['101-500'] || 0,
                likesDist['500+'] || 0
            ];
            likesChart.update();
            
            // 更新情感分析图表
            const sentiment = analytics.sentiment_analysis || {};
            sentimentChart.data.datasets[0].data = [
                sentiment.positive || 0,
                sentiment.negative || 0,
                sentiment.neutral || 0
            ];
            sentimentChart.update();
        }
        
        // 显示指定页的评论
        function displayCommentsPage(page) {
            currentPage = page;
            const commentsToShow = filteredComments.length > 0 ? filteredComments : allComments;
            const startIndex = (page - 1) * commentsPerPage;
            const endIndex = startIndex + commentsPerPage;
            const pageComments = commentsToShow.slice(startIndex, endIndex);
            
            console.log(`显示第${page}页评论:`, pageComments.length, '条');
            
            // 显示评论
            displayComments(pageComments);
            
            // 更新分页控件
            updatePagination();
            
            // 更新状态信息
            const totalPages = Math.ceil(commentsToShow.length / commentsPerPage);
            const searchInfo = currentSearchQuery ? `（搜索: "${currentSearchQuery}"）` : '';
            document.getElementById('status').textContent = `第 ${page} 页，共 ${totalPages} 页，显示 ${pageComments.length} 条评论 ${searchInfo} - 三列布局样式`;
        }
        
        // 显示评论列表
        function displayComments(comments) {
            const commentsList = document.getElementById('comments-list');
            commentsList.innerHTML = '';
            
            if (!comments || comments.length === 0) {
                commentsList.innerHTML = '<div class="status">暂无评论数据</div>';
                return;
            }
            
            // 创建网格容器
            const commentsGrid = document.createElement('div');
            commentsGrid.className = 'comments-grid';
            
            comments.forEach((comment, index) => {
                const commentDiv = document.createElement('div');
                commentDiv.className = 'comment-item';
                
                // 评论内容处理
                const content = comment['评论内容'] || '';
                const isLongContent = content.length > 80;
                const shortContent = isLongContent ? content.substring(0, 80) + '...' : content;
                const contentId = `content-${index}`;
                const expandBtnId = `expand-btn-${index}`;
                
                // 处理评论图片
                const commentImages = comment['评论图片'] || '';
                const imageUrls = commentImages ? commentImages.split(',').filter(url => url.trim()) : [];
                let imagesHtml = '';
                if (imageUrls.length > 0) {
                    imagesHtml = '<div class="comment-images">';
                    imageUrls.forEach((url, imgIndex) => {
                        imagesHtml += `
                            <div class="comment-image-wrapper">
                                <img src="${url.trim()}" alt="评论图片" class="comment-image" 
                                     onclick="showImageModal('${url.trim()}')" 
                                     onerror="this.style.display='none'" 
                                     loading="lazy">
                            </div>
                        `;
                    });
                    imagesHtml += '</div>';
                }
                
                // 检查是否有回复
                const hasReply = comment['被回复人昵称'] && comment['被回复人昵称'].trim() !== '';
                
                commentDiv.innerHTML = `
                    <div class="comment-user">${comment['用户昵称'] || 'Unknown'}</div>
                    <div class="comment-content" id="${contentId}">
                        ${shortContent}
                        ${isLongContent ? `<span class="expand-btn" id="${expandBtnId}" onclick="toggleContent('${contentId}', '${expandBtnId}', \`${content.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`, \`${shortContent}\`)">展开</span>` : ''}
                    </div>
                    ${imagesHtml}
                    <div class="comment-meta">
                        <div class="meta-item">
                            <i class="fas fa-heart"></i>
                            <span>${comment['点赞数'] || 0}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-map-marker-alt"></i>
                            <span>${comment['ip归属'] || '未知'}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-clock"></i>
                            <span>${comment['评论时间'] ? comment['评论时间'].substring(5, 16) : ''}</span>
                        </div>
                        ${hasReply ? `
                        <div class="meta-item reply-indicator" onclick="showReplyDetails('${comment['评论时间']}', '${comment['用户昵称']}', '${comment['被回复人昵称']}')">
                            <i class="fas fa-reply"></i>
                            <span>回复: @${comment['被回复人昵称']} <strong>(点击查看)</strong></span>
                        </div>
                        ` : ''}
                        ${comment['作者已赞'] === '是' ? `
                        <div class="meta-item">
                            <i class="fas fa-star"></i>
                            <span>作者已赞</span>
                        </div>
                        ` : ''}
                    </div>
                `;
                commentsGrid.appendChild(commentDiv);
            });
            
            commentsList.appendChild(commentsGrid);
        }
        
        // 切换评论内容展开/收起
        function toggleContent(contentId, btnId, fullContent, shortContent) {
            const contentElement = document.getElementById(contentId);
            const btnElement = document.getElementById(btnId);
            
            if (btnElement.textContent === '展开') {
                contentElement.innerHTML = fullContent + `<span class="expand-btn" id="${btnId}" onclick="toggleContent('${contentId}', '${btnId}', \`${fullContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`, \`${shortContent}\`)">收起</span>`;
            } else {
                contentElement.innerHTML = shortContent + `<span class="expand-btn" id="${btnId}" onclick="toggleContent('${contentId}', '${btnId}', \`${fullContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`, \`${shortContent}\`)">展开</span>`;
            }
        }
        
        // 显示作者已赞评论页面
        function displayAuthorLikedCommentsPage(page) {
            authorLikedCurrentPage = page;
            const commentsToShow = authorLikedComments;
            const startIndex = (page - 1) * commentsPerPage;
            const endIndex = startIndex + commentsPerPage;
            const pageComments = commentsToShow.slice(startIndex, endIndex);
            
            console.log(`显示作者已赞评论第${page}页:`, pageComments.length, '条');
            
            // 显示评论
            displayAuthorLikedComments(pageComments);
            
            // 更新分页控件
            updateAuthorLikedPagination();
            
            // 更新状态信息
            const totalPages = Math.ceil(commentsToShow.length / commentsPerPage);
            document.getElementById('author-liked-status').textContent = `第 ${page} 页，共 ${totalPages} 页，显示 ${pageComments.length} 条作者已赞评论 - 三列布局样式`;
        }
        
        // 显示作者已赞评论列表
        function displayAuthorLikedComments(comments) {
            const commentsList = document.getElementById('author-liked-list');
            commentsList.innerHTML = '';
            
            if (!comments || comments.length === 0) {
                commentsList.innerHTML = '<div class="status">暂无作者已赞评论数据</div>';
                return;
            }
            
            // 创建网格容器
            const commentsGrid = document.createElement('div');
            commentsGrid.className = 'comments-grid';
            
            comments.forEach((comment, index) => {
                const commentDiv = document.createElement('div');
                commentDiv.className = 'comment-item';
                
                // 评论内容处理
                const content = comment['评论内容'] || '';
                const isLongContent = content.length > 80;
                const shortContent = isLongContent ? content.substring(0, 80) + '...' : content;
                const contentId = `author-liked-content-${index}`;
                const expandBtnId = `author-liked-expand-btn-${index}`;
                
                // 处理评论图片
                const commentImages = comment['评论图片'] || '';
                const imageUrls = commentImages ? commentImages.split(',').filter(url => url.trim()) : [];
                let imagesHtml = '';
                if (imageUrls.length > 0) {
                    imagesHtml = '<div class="comment-images">';
                    imageUrls.forEach((url, imgIndex) => {
                        imagesHtml += `
                            <div class="comment-image-wrapper">
                                <img src="${url.trim()}" alt="评论图片" class="comment-image" 
                                     onclick="showImageModal('${url.trim()}')" 
                                     onerror="this.style.display='none'" 
                                     loading="lazy">
                            </div>
                        `;
                    });
                    imagesHtml += '</div>';
                }
                
                // 检查是否有回复
                const hasReply = comment['被回复人昵称'] && comment['被回复人昵称'].trim() !== '';
                
                commentDiv.innerHTML = `
                    <div class="comment-user">${comment['用户昵称'] || 'Unknown'}</div>
                    <div class="comment-content" id="${contentId}">
                        ${shortContent}
                        ${isLongContent ? `<span class="expand-btn" id="${expandBtnId}" onclick="toggleAuthorLikedContent('${contentId}', '${expandBtnId}', \`${content.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`, \`${shortContent}\`)">展开</span>` : ''}
                    </div>
                    ${imagesHtml}
                    <div class="comment-meta">
                        <div class="meta-item">
                            <i class="fas fa-heart"></i>
                            <span>${comment['点赞数'] || 0}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-map-marker-alt"></i>
                            <span>${comment['ip归属'] || '未知'}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-clock"></i>
                            <span>${comment['评论时间'] ? comment['评论时间'].substring(5, 16) : ''}</span>
                        </div>
                        ${hasReply ? `
                        <div class="meta-item reply-indicator" onclick="showReplyDetails('${comment['评论时间']}', '${comment['用户昵称']}', '${comment['被回复人昵称']}')">
                            <i class="fas fa-reply"></i>
                            <span>回复: @${comment['被回复人昵称']} <strong>(点击查看)</strong></span>
                        </div>
                        ` : ''}
                        <div class="meta-item">
                            <i class="fas fa-star"></i>
                            <span>作者已赞</span>
                        </div>
                    </div>
                `;
                commentsGrid.appendChild(commentDiv);
            });
            
            commentsList.appendChild(commentsGrid);
        }
        
        // 切换作者已赞评论内容展开/收起
        function toggleAuthorLikedContent(contentId, btnId, fullContent, shortContent) {
            const contentElement = document.getElementById(contentId);
            const btnElement = document.getElementById(btnId);
            
            if (btnElement.textContent === '展开') {
                contentElement.innerHTML = fullContent + `<span class="expand-btn" id="${btnId}" onclick="toggleAuthorLikedContent('${contentId}', '${btnId}', \`${fullContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`, \`${shortContent}\`)">收起</span>`;
            } else {
                contentElement.innerHTML = shortContent + `<span class="expand-btn" id="${btnId}" onclick="toggleAuthorLikedContent('${contentId}', '${btnId}', \`${fullContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`, \`${shortContent}\`)">展开</span>`;
            }
        }
        
        // 更新作者已赞评论分页控件
        function updateAuthorLikedPagination() {
            const paginationContainer = document.getElementById('author-liked-pagination');
            const commentsToShow = authorLikedComments;
            const totalPages = Math.ceil(commentsToShow.length / commentsPerPage);
            
            console.log('更新作者已赞分页控件:', authorLikedCurrentPage, '/', totalPages);
            
            if (totalPages <= 1) {
                paginationContainer.innerHTML = '';
                return;
            }
            
            let html = '';
            
            // 上一页按钮
            html += `<button class="pagination-btn" ${authorLikedCurrentPage <= 1 ? 'disabled' : ''} onclick="displayAuthorLikedCommentsPage(${authorLikedCurrentPage - 1})">
                <i class="fas fa-chevron-left"></i> 上一页
            </button>`;
            
            // 页码按钮
            let startPage = Math.max(1, authorLikedCurrentPage - 2);
            let endPage = Math.min(totalPages, authorLikedCurrentPage + 2);
            
            if (startPage > 1) {
                html += `<button class="pagination-btn" onclick="displayAuthorLikedCommentsPage(1)">1</button>`;
                if (startPage > 2) {
                    html += '<span class="pagination-info">...</span>';
                }
            }
            
            for (let i = startPage; i <= endPage; i++) {
                html += `<button class="pagination-btn ${i === authorLikedCurrentPage ? 'active' : ''}" onclick="displayAuthorLikedCommentsPage(${i})">${i}</button>`;
            }
            
            if (endPage < totalPages) {
                if (endPage < totalPages - 1) {
                    html += '<span class="pagination-info">...</span>';
                }
                html += `<button class="pagination-btn" onclick="displayAuthorLikedCommentsPage(${totalPages})">${totalPages}</button>`;
            }
            
            // 下一页按钮
            html += `<button class="pagination-btn" ${authorLikedCurrentPage >= totalPages ? 'disabled' : ''} onclick="displayAuthorLikedCommentsPage(${authorLikedCurrentPage + 1})">
                下一页 <i class="fas fa-chevron-right"></i>
            </button>`;
            
            // 评论数信息
            const totalComments = commentsToShow.length;
            html += `<span class="pagination-info">共 ${totalComments} 条作者已赞评论</span>`;
            
            paginationContainer.innerHTML = html;
        }
        function showImageModal(imageUrl) {
            // 创建模态窗口
            const modal = document.createElement('div');
            modal.className = 'image-modal';
            
            modal.innerHTML = `
                <span class="close-btn" onclick="this.closest('.image-modal').remove()">&times;</span>
                <img src="${imageUrl}" alt="评论图片" onerror="this.closest('.image-modal').remove(); alert('图片加载失败');">
            `;
            
            document.body.appendChild(modal);
            
            // 点击模态窗口外部或ESC键关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
            
            // ESC键关闭
            const handleKeyPress = (e) => {
                if (e.key === 'Escape') {
                    modal.remove();
                    document.removeEventListener('keydown', handleKeyPress);
                }
            };
            document.addEventListener('keydown', handleKeyPress);
        }
        
        // 显示回复详情
        function showReplyDetails(commentTime, userName, repliedUserName) {
            // 找到被点击的这条评论（二级评论）
            const clickedComment = allComments.find(comment => 
                comment['用户昵称'] === userName && 
                comment['评论时间'] === commentTime
            );
            
            if (!clickedComment) {
                alert('未找到评论');
                return;
            }
            
            // 获取父评论ID，用于精确匹配原始评论
            const parentCommentId = clickedComment['父评论ID'];
            
            let originalComment = null;
            
            if (parentCommentId && parentCommentId !== '0') {
                // 通过父评论ID精确查找原始评论
                originalComment = allComments.find(comment => 
                    comment['评论ID'] === parentCommentId
                );
                
                console.log('通过父评论ID查找原始评论:', parentCommentId, originalComment);
            }
            
            // 如果通过父评论ID找不到，尝试通过被回复人昵称查找（备用方案）
            if (!originalComment) {
                console.log('未通过父评论ID找到原始评论，使用备用方案查找');
                
                // 查找该用户的一级评论（父评论ID为空或0的评论）
                const userComments = allComments.filter(comment => 
                    comment['用户昵称'] === repliedUserName &&
                    (!comment['父评论ID'] || comment['父评论ID'] === '0')
                );
                
                if (userComments.length > 0) {
                    // 按时间排序，取最近的一级评论
                    userComments.sort((a, b) => {
                        const timeA = parseCommentTime(a['评论时间'] || '');
                        const timeB = parseCommentTime(b['评论时间'] || '');
                        return timeB - timeA; // 降序排列，最新的在前
                    });
                    originalComment = userComments[0];
                    console.log('通过备用方案找到原始评论:', originalComment);
                }
            }
            
            if (!originalComment) {
                alert(`未找到被回复的原始评论\n\n调试信息:\n- 当前评论作者: ${userName}\n- 被回复人: ${repliedUserName}\n- 父评论ID: ${parentCommentId || '无'}`);
                return;
            }
            
            // 创建模态窗口显示对话
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            `;
            
            const modalContent = document.createElement('div');
            modalContent.style.cssText = `
                background: white;
                border-radius: 12px;
                padding: 20px;
                max-width: 600px;
                max-height: 80%;
                overflow-y: auto;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            `;
            
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">
                    <h3 style="margin: 0; color: #333;">💬 评论对话</h3>
                    <button onclick="this.closest('.modal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999;">&times;</button>
                </div>
                
                <div style="margin-bottom: 20px; padding: 15px; background: #f8f9ff; border-left: 4px solid #667eea; border-radius: 8px;">
                    <div style="font-weight: bold; color: #667eea; margin-bottom: 8px;">📝 原始评论 (${originalComment['用户昵称']})</div>
                    <div style="color: #333; line-height: 1.5; margin-bottom: 10px;">${originalComment['评论内容'] || ''}</div>
                    ${(() => {
                        const originalImages = originalComment['评论图片'] || '';
                        const originalImageUrls = originalImages ? originalImages.split(',').filter(url => url.trim()) : [];
                        if (originalImageUrls.length > 0) {
                            let imagesHtml = '<div style="margin: 10px 0; display: flex; gap: 5px; flex-wrap: wrap;">';
                            originalImageUrls.forEach(url => {
                                imagesHtml += `<img src="${url.trim()}" alt="评论图片" 
                                    style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px; cursor: pointer;" 
                                    onclick="showImageModal('${url.trim()}')" 
                                    onerror="this.style.display='none'">`;
                            });
                            imagesHtml += '</div>';
                            return imagesHtml;
                        }
                        return '';
                    })()} 
                    <div style="font-size: 0.85em; color: #666; display: flex; gap: 15px;">
                        <span><i class="fas fa-heart"></i> ${originalComment['点赞数'] || 0}</span>
                        <span><i class="fas fa-map-marker-alt"></i> ${originalComment['ip归属'] || '未知'}</span>
                        <span><i class="fas fa-clock"></i> ${originalComment['评论时间'] ? originalComment['评论时间'].substring(5, 16) : ''}</span>
                    </div>
                </div>
                
                <div style="padding: 15px; background: #fff8e1; border-left: 4px solid #ffa726; border-radius: 8px;">
                    <div style="font-weight: bold; color: #f57c00; margin-bottom: 8px;">💬 回复评论 (${clickedComment['用户昵称']})</div>
                    <div style="color: #333; line-height: 1.5; margin-bottom: 10px;">回复 @${clickedComment['被回复人昵称']}: ${clickedComment['评论内容'] || ''}</div>
                    ${(() => {
                        const replyImages = clickedComment['评论图片'] || '';
                        const replyImageUrls = replyImages ? replyImages.split(',').filter(url => url.trim()) : [];
                        if (replyImageUrls.length > 0) {
                            let imagesHtml = '<div style="margin: 10px 0; display: flex; gap: 5px; flex-wrap: wrap;">';
                            replyImageUrls.forEach(url => {
                                imagesHtml += `<img src="${url.trim()}" alt="评论图片" 
                                    style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px; cursor: pointer;" 
                                    onclick="showImageModal('${url.trim()}')" 
                                    onerror="this.style.display='none'">`;
                            });
                            imagesHtml += '</div>';
                            return imagesHtml;
                        }
                        return '';
                    })()} 
                    <div style="font-size: 0.85em; color: #666; display: flex; gap: 15px;">
                        <span><i class="fas fa-heart"></i> ${clickedComment['点赞数'] || 0}</span>
                        <span><i class="fas fa-map-marker-alt"></i> ${clickedComment['ip归属'] || '未知'}</span>
                        <span><i class="fas fa-clock"></i> ${clickedComment['评论时间'] ? clickedComment['评论时间'].substring(5, 16) : ''}</span>
                    </div>
                </div>
            `;
            
            modal.className = 'modal';
            modal.appendChild(modalContent);
            document.body.appendChild(modal);
            
            // 点击模态窗口外部关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
        }
        
        // 更新分页控件
        function updatePagination() {
            const paginationContainer = document.getElementById('comments-pagination');
            const commentsToShow = filteredComments.length > 0 ? filteredComments : allComments;
            const totalPages = Math.ceil(commentsToShow.length / commentsPerPage);
            
            console.log('更新分页控件:', currentPage, '/', totalPages);
            
            if (totalPages <= 1 && !currentSearchQuery) {
                paginationContainer.innerHTML = '';
                return;
            }
            
            let html = '';
            
            // 只有在有多页时才显示分页按钮
            if (totalPages > 1) {
                // 上一页按钮
                html += `<button class="pagination-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="displayCommentsPage(${currentPage - 1})">
                    <i class="fas fa-chevron-left"></i> 上一页
                </button>`;
                
                // 页码按钮
                let startPage = Math.max(1, currentPage - 2);
                let endPage = Math.min(totalPages, currentPage + 2);
                
                if (startPage > 1) {
                    html += `<button class="pagination-btn" onclick="displayCommentsPage(1)">1</button>`;
                    if (startPage > 2) {
                        html += '<span class="pagination-info">...</span>';
                    }
                }
                
                for (let i = startPage; i <= endPage; i++) {
                    html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="displayCommentsPage(${i})">${i}</button>`;
                }
                
                if (endPage < totalPages) {
                    if (endPage < totalPages - 1) {
                        html += '<span class="pagination-info">...</span>';
                    }
                    html += `<button class="pagination-btn" onclick="displayCommentsPage(${totalPages})">${totalPages}</button>`;
                }
                
                // 下一页按钮
                html += `<button class="pagination-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="displayCommentsPage(${currentPage + 1})">
                    下一页 <i class="fas fa-chevron-right"></i>
                </button>`;
            }
            
            // 评论数信息
            const totalComments = commentsToShow.length;
            const searchInfo = currentSearchQuery ? `（搜索结果）` : '';
            html += `<span class="pagination-info">共 ${totalComments} 条评论 ${searchInfo}</span>`;
            
            // 搜索控件
            html += `
                <div class="search-container">
                    <i class="fas fa-search"></i>
                    <input type="text" class="search-input" 
                           placeholder="输入用户昵称搜索..." 
                           value="${currentSearchQuery}" 
                           onkeypress="if(event.key==='Enter') searchComments()">
                    <button class="search-btn" onclick="searchComments()">
                        <i class="fas fa-search"></i> 搜索
                    </button>
                    ${currentSearchQuery ? '<button class="clear-btn" onclick="clearSearch()"><i class="fas fa-times"></i> 清除</button>' : ''}
                </div>
            `;
            
            paginationContainer.innerHTML = html;
        }
        
        // 搜索评论功能
        function searchComments() {
            const searchInput = document.querySelector('.search-input');
            const query = searchInput.value.trim();
            
            console.log('搜索关键词:', query);
            
            if (query === '') {
                clearSearch();
                return;
            }
            
            // 过滤评论，搜索用户昵称中包含关键词的评论
            filteredComments = allComments.filter(comment => {
                const username = comment['用户昵称'] || '';
                return username.toLowerCase().includes(query.toLowerCase());
            });
            
            // 按时间排序（最新的在前）
            filteredComments.sort((a, b) => {
                const timeA = parseCommentTime(a['评论时间'] || '');
                const timeB = parseCommentTime(b['评论时间'] || '');
                return timeB - timeA; // 降序排列
            });
            
            currentSearchQuery = query;
            currentPage = 1; // 重置到第一页
            
            console.log(`搜索到 ${filteredComments.length} 条包含 "${query}" 的评论`);
            
            // 显示搜索结果
            displayCommentsPage(1);
        }
        
        // 解析评论时间的辅助函数
        function parseCommentTime(timeStr) {
            try {
                if (!timeStr) return new Date(0);
                return new Date(timeStr);
            } catch {
                return new Date(0);
            }
        }
        
        // 清除搜索功能
        function clearSearch() {
            filteredComments = [];
            currentSearchQuery = '';
            currentPage = 1;
            
            console.log('清除搜索，显示所有评论');
            
            // 显示所有评论
            displayCommentsPage(1);
        }
        function updateCommentsList(comments) {
            const commentsList = document.getElementById('comments-list');
            commentsList.innerHTML = '';
            
            if (!comments || comments.length === 0) {
                commentsList.innerHTML = '<div class="status">暂无评论数据</div>';
                return;
            }
            
            // 显示最新20条评论
            const recentComments = comments.slice(0, 20);
            
            recentComments.forEach(comment => {
                const commentDiv = document.createElement('div');
                commentDiv.className = 'comment-item';
                commentDiv.innerHTML = `
                    <div class="comment-user">${comment['用户昵称'] || 'Unknown'}</div>
                    <div class="comment-content">${comment['评论内容'] || ''}</div>
                    ${(() => {
                        const commentImages = comment['评论图片'] || '';
                        const imageUrls = commentImages ? commentImages.split(',').filter(url => url.trim()) : [];
                        if (imageUrls.length > 0) {
                            let imagesHtml = '<div class="comment-images">';
                            imageUrls.forEach(url => {
                                imagesHtml += `
                                    <div class="comment-image-wrapper">
                                        <img src="${url.trim()}" alt="评论图片" class="comment-image" 
                                             onclick="showImageModal('${url.trim()}')" 
                                             onerror="this.style.display='none'" 
                                             loading="lazy">
                                    </div>
                                `;
                            });
                            imagesHtml += '</div>';
                            return imagesHtml;
                        }
                        return '';
                    })()} 
                    <div class="comment-meta">
                        <div class="meta-item">
                            <i class="fas fa-heart"></i>
                            <span>${comment['点赞数'] || 0}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-map-marker-alt"></i>
                            <span>${comment['ip归属'] || '未知'}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-clock"></i>
                            <span>${comment['评论时间'] || ''}</span>
                        </div>
                        ${comment['被回复人昵称'] ? `
                        <div class="meta-item">
                            <i class="fas fa-reply"></i>
                            <span>回复: @${comment['被回复人昵称']}</span>
                        </div>
                        ` : ''}
                        ${comment['作者已赞'] === '是' ? `
                        <div class="meta-item">
                            <i class="fas fa-star"></i>
                            <span>作者已赞</span>
                        </div>
                        ` : ''}
                    </div>
                `;
                commentsList.appendChild(commentDiv);
            });
        }
        
        // 更新用户列表
        function updateUsersList(users) {
            const usersList = document.getElementById('users-list');
            usersList.innerHTML = '';
            
            if (!users || users.length === 0) {
                usersList.innerHTML = '<div class="status">暂无用户数据</div>';
                return;
            }
            
            usersList.innerHTML = '<div class="user-list">';
            users.forEach(user => {
                const userDiv = document.createElement('div');
                userDiv.className = 'user-item';
                userDiv.innerHTML = `
                    <div class="user-name">${user.user}</div>
                    <div class="user-count">${user.count} 条评论</div>
                `;
                usersList.querySelector('.user-list').appendChild(userDiv);
            });
            usersList.innerHTML += '</div>';
        }
        
        // 更新地区列表
        function updateLocationsList(locations) {
            const locationsList = document.getElementById('locations-list');
            locationsList.innerHTML = '';
            
            if (!locations || Object.keys(locations).length === 0) {
                locationsList.innerHTML = '<div class="status">暂无地区数据</div>';
                return;
            }
            
            locationsList.innerHTML = '<div class="location-list">';
            Object.entries(locations).forEach(([location, count]) => {
                const locationDiv = document.createElement('div');
                locationDiv.className = 'location-item';
                locationDiv.innerHTML = `
                    <div class="location-name">${location}</div>
                    <div class="location-count">${count} 条</div>
                `;
                locationsList.querySelector('.location-list').appendChild(locationDiv);
            });
            locationsList.innerHTML += '</div>';
        }
        
        // 更新词云
        function updateWordCloud(wordCloudData) {
            const container = document.getElementById('wordCloudContainer');
            if (wordCloudData) {
                container.innerHTML = `<img src="${wordCloudData}" class="word-cloud-img" alt="词云图">`;
            } else {
                container.innerHTML = '<div class="status">暂无词云数据</div>';
            }
        }
        
        // 切换标签页
        function switchTab(tabName) {
            // 隐藏所有标签页内容
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // 显示选中的标签页
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
            
            // 如果是评论标签页，确保显示分页和搜索结果
            if (tabName === 'comments' && allComments.length > 0) {
                displayCommentsPage(currentPage);
            }
            
            // 如果是作者已赞标签页，显示作者已赞评论
            if (tabName === 'author-liked' && authorLikedComments.length > 0) {
                displayAuthorLikedCommentsPage(authorLikedCurrentPage);
            }
        }
        
        // 导出数据
        function exportData(format) {
            if (!currentData) {
                alert('暂无数据可导出');
                return;
            }
            
            const url = `/export/${format}`;
            const link = document.createElement('a');
            link.href = url;
            link.download = `douyin_comments.${format}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        // 页面加载完成后初始化
        window.onload = function() {
            initCharts();
            loadData();
            
            // 取消自动刷新，用户手动刷新
            // setInterval(loadData, 15000);
        };
    </script>
</body>
</html>
        """
        
        with open(os.path.join(self.web_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)

    async def _update_web_data(self):
        """更新Web数据文件"""
        try:
            data_file = os.path.join(self.web_path, 'data.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data_cache, f, ensure_ascii=False, indent=2)
            utils.logger.info(f"[DouyinWebStore] Web数据已更新，当前评论数: {self.data_cache['stats']['total_comments']}")
        except Exception as e:
            utils.logger.error(f"[DouyinWebStore] 更新Web数据失败: {e}")