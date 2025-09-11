import requests
import json

try:
    # 测试8082端口的API接口
    print("🧪 测试8082端口Web服务器API接口...")
    
    # 测试主数据接口
    response = requests.get("http://localhost:8082/data.json", timeout=5)
    print(f"📡 API响应状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📊 数据结构:")
        print(f"   - 评论数量: {len(data.get('comments', []))}")
        print(f"   - 统计信息: {data.get('stats', {})}")
        
        # 检查作者赞过的评论
        author_liked_count = 0
        for comment in data.get('comments', []):
            if comment.get('作者已赞', '') == '是':
                author_liked_count += 1
        print(f"   - 作者赞过评论数: {author_liked_count}")
        
        # 测试分页API
        print("\n📄 测试分页API:")
        page_response = requests.get("http://localhost:8082/api/comments?page=1", timeout=5)
        if page_response.status_code == 200:
            page_data = page_response.json()
            print(f"   - 第1页评论数: {len(page_data.get('comments', []))}")
            print(f"   - 分页信息: {page_data.get('pagination', {})}")
        else:
            print(f"❌ 分页API失败: {page_response.status_code}")
            
        # 测试作者赞过的评论API
        print("\n❤️ 测试作者赞过的评论API:")
        liked_response = requests.get("http://localhost:8082/api/author-liked?page=1", timeout=5)
        if liked_response.status_code == 200:
            liked_data = liked_response.json()
            print(f"   - 第1页作者赞过评论数: {len(liked_data.get('comments', []))}")
            print(f"   - 分页信息: {liked_data.get('pagination', {})}")
        else:
            print(f"❌ 作者赞过的评论API失败: {liked_response.status_code}")
            
    else:
        print(f"❌ API请求失败: {response.status_code}")
        print(f"📝 响应内容: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")