import json
import os
from datetime import datetime

# 加载现有数据
data_file = 'data/douyin/web/data.json'
with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

comments = data.get('comments', [])
print(f'处理 {len(comments)} 条评论')

# 计算统计信息
total_comments = len(comments)
unique_users = len(set(c.get('用户昵称', '') for c in comments))
total_likes = sum(int(c.get('点赞数', 0)) for c in comments)
avg_likes = round(total_likes / max(1, total_comments), 2)
reply_count = sum(1 for c in comments if c.get('被回复人昵称', ''))
reply_ratio = round(reply_count / max(1, total_comments) * 100, 2)
author_liked_count = sum(1 for c in comments if c.get('作者已赞', '') == '是')

# 添加统计信息
data['stats'] = {
    'total_comments': total_comments,
    'unique_users': unique_users,
    'total_likes': total_likes,
    'avg_likes': avg_likes,
    'reply_ratio': reply_ratio,
    'author_liked_count': author_liked_count,
    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# 添加基础分析数据
data['analytics'] = {
    'time_distribution': {'labels': [], 'data': []},
    'likes_distribution': [0, 0, 0, 0, 0],
    'sentiment_analysis': [0, 0, 0],
    'location_distribution': {},
    'word_cloud': '',
    'top_users': [],
    'recent_comments': []
}

# 保存文件
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'✅ 统计信息已更新:')
print(f'  - 总评论数: {total_comments}')
print(f'  - 参与用户: {unique_users}')
print(f'  - 总点赞数: {total_likes}')
print(f'  - 平均点赞数: {avg_likes}')
print(f'  - 回复比例: {reply_ratio}%')
print(f'  - 作者点赞数: {author_liked_count}')