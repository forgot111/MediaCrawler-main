# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# 抖音平台配置
PUBLISH_TIME_TYPE = 0

# 指定DY视频ID列表
DY_SPECIFIED_ID_LIST = [
    "7548310409170783498",
    # ........................
]

# 指定DY用户ID列表    
DY_CREATOR_ID_LIST = [
    "MS4wLjABAAAA0AiK9Q4FlkTxKHo-b6Vi1ckA2Ybq-WNgJ-b5xXlULtI",
    # ........................
]
#uv run main.py --platform dy --lt qrcode --type detail
#uv run python start_douyin_complete.py
#uv run python start_web_auto_port.py
#uv run python start_image_web.py  # 启动支持评论图片显示的Web界面
#7548310409170783498