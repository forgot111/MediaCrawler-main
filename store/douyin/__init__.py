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
# @Desc    :
from typing import List, Dict

import config
from var import source_keyword_var

from .douyin_store_impl import *
from .douyin_store_media import *

# 用于缓存评论信息，key为comment_id，value为评论信息
comment_cache: Dict[str, Dict] = {}
# 用于记录已处理的评论ID，避免重复处理
processed_comments: set = set()


class DouyinStoreFactory:
    STORES = {
        "csv": DouyinCsvStoreImplement,
        "db": DouyinDbStoreImplement,
        "json": DouyinJsonStoreImplement,
        "sqlite": DouyinSqliteStoreImplement,
    }
    
    # 单例模式，确保所有并发任务使用同一个存储实例
    _instance = None
    _lock = asyncio.Lock()

    @classmethod
    async def create_store(cls) -> AbstractStore:
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    store_class = cls.STORES.get(config.SAVE_DATA_OPTION)
                    if not store_class:
                        raise ValueError("[DouyinStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite ...")
                    cls._instance = store_class()
        return cls._instance


def _extract_note_image_list(aweme_detail: Dict) -> List[str]:
    """
    提取笔记图片列表

    Args:
        aweme_detail (Dict): 抖音内容详情

    Returns:
        List[str]: 笔记图片列表
    """
    images_res: List[str] = []
    images: List[Dict] = aweme_detail.get("images", [])

    if not images:
        return []

    for image in images:
        image_url_list = image.get("url_list", [])  # download_url_list 为带水印的图片，url_list 为无水印的图片
        if image_url_list:
            images_res.append(image_url_list[-1])

    return images_res


def _extract_comment_image_list(comment_item: Dict) -> List[str]:
    """
    提取评论图片列表

    Args:
        comment_item (Dict): 抖音评论

    Returns:
        List[str]: 评论图片列表
    """
    images_res: List[str] = []
    image_list: List[Dict] = comment_item.get("image_list", [])

    if not image_list:
        return []

    for image in image_list:
        image_url_list = image.get("origin_url", {}).get("url_list", [])
        if image_url_list and len(image_url_list) > 1:
            images_res.append(image_url_list[1])

    return images_res


def _extract_content_cover_url(aweme_detail: Dict) -> str:
    """
    提取视频封面地址

    Args:
        aweme_detail (Dict): 抖音内容详情

    Returns:
        str: 视频封面地址
    """
    res_cover_url = ""

    video_item = aweme_detail.get("video", {})
    raw_cover_url_list = (video_item.get("raw_cover", {}) or video_item.get("origin_cover", {})).get("url_list", [])
    if raw_cover_url_list and len(raw_cover_url_list) > 1:
        res_cover_url = raw_cover_url_list[1]

    return res_cover_url


def _extract_video_download_url(aweme_detail: Dict) -> str:
    """
    提取视频下载地址

    Args:
        aweme_detail (Dict): 抖音视频

    Returns:
        str: 视频下载地址
    """
    video_item = aweme_detail.get("video", {})
    url_h264_list = video_item.get("play_addr_h264", {}).get("url_list", [])
    url_256_list = video_item.get("play_addr_256", {}).get("url_list", [])
    url_list = video_item.get("play_addr", {}).get("url_list", [])
    actual_url_list = url_h264_list or url_256_list or url_list
    if not actual_url_list or len(actual_url_list) < 2:
        return ""
    return actual_url_list[-1]


def _extract_music_download_url(aweme_detail: Dict) -> str:
    """
    提取音乐下载地址

    Args:
        aweme_detail (Dict): 抖音视频

    Returns:
        str: 音乐下载地址
    """
    music_item = aweme_detail.get("music", {})
    play_url = music_item.get("play_url", {})
    music_url = play_url.get("uri", "")
    return music_url


async def update_douyin_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {})
    interact_info = aweme_item.get("statistics", {})
    save_content_item = {
        "aweme_id": aweme_id,
        "aweme_type": str(aweme_item.get("aweme_type")),
        "title": aweme_item.get("desc", ""),
        "desc": aweme_item.get("desc", ""),
        "发布时间": utils.get_time_str_from_unix_time(aweme_item.get("create_time")),
        "user_id": user_info.get("uid"),
        "sec_uid": user_info.get("sec_uid"),
        "short_user_id": user_info.get("short_id"),
        "user_unique_id": user_info.get("unique_id"),
        "user_signature": user_info.get("signature"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("avatar_thumb", {}).get("url_list", [""])[0],
        "liked_count": str(interact_info.get("digg_count")),
        "collected_count": str(interact_info.get("collect_count")),
        "comment_count": str(interact_info.get("comment_count")),
        "share_count": str(interact_info.get("share_count")),
        "ip_location": aweme_item.get("ip_label", ""),
        "last_modify_ts": utils.get_current_timestamp(),
        "aweme_url": f"https://www.douyin.com/video/{aweme_id}",
        "cover_url": _extract_content_cover_url(aweme_item),
        "video_download_url": _extract_video_download_url(aweme_item),
        "music_download_url": _extract_music_download_url(aweme_item),
        "note_download_url": ",".join(_extract_note_image_list(aweme_item)),
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(f"[store.douyin.update_douyin_aweme] douyin aweme id:{aweme_id}, title:{save_content_item.get('title')}")
    store = await DouyinStoreFactory.create_store()
    await store.store_content(content_item=save_content_item)


async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    
    utils.logger.info(f"[store.douyin.batch_update_dy_aweme_comments] 开始处理视频 {aweme_id} 的 {len(comments)} 条评论")
    
    for comment_item in comments:
        await update_dy_aweme_comment(aweme_id, comment_item)
    
    # 显示当前缓存状态
    utils.logger.info(f"[store.douyin.batch_update_dy_aweme_comments] 当前缓存了 {len(comment_cache)} 条评论信息，已处理 {len(processed_comments)} 条评论")
    
    # 后处理：更新那些父评论ID存在但父评论信息已经缓存的回复评论
    await update_pending_reply_comments(aweme_id)


async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict):
    comment_aweme_id = comment_item.get("aweme_id")
    if aweme_id != comment_aweme_id:
        utils.logger.error(f"[store.douyin.update_dy_aweme_comment] comment_aweme_id: {comment_aweme_id} != aweme_id: {aweme_id}")
        return
    
    user_info = comment_item.get("user", {})
    comment_id = comment_item.get("cid")
    parent_comment_id = comment_item.get("reply_id", "0")
    
    # 检查是否已经处理过这个评论，避免重复
    if comment_id in processed_comments:
        utils.logger.warning(f"[store.douyin.update_dy_aweme_comment] 评论 {comment_id} 已处理过，跳过重复处理")
        return
    
    # 标记为已处理
    processed_comments.add(comment_id)
    # 减少日志输出频率，每50条评论输出一次
    if len(processed_comments) % 50 == 0:
        utils.logger.info(f"[store.douyin.update_dy_aweme_comment] 已处理 {len(processed_comments)} 条评论")
    
    # 先缓存当前评论信息
    comment_cache[comment_id] = {
        "comment_id": comment_id,
        "user_nickname": user_info.get("nickname", ""),
        "user_info": user_info,
        "content": comment_item.get("text", ""),
    }
    
    # 尝试获取被回复人的昵称与内容（仅当该评论为回复时才可能存在）
    replied_user_nickname = ""
    replied_user_content = ""
    
    if parent_comment_id != "0":
        # 这是回复评论，根据父评论ID查找父评论的用户昵称
        if parent_comment_id in comment_cache:
            parent_comment = comment_cache[parent_comment_id]
            replied_user_nickname = parent_comment.get("user_nickname", "")
            replied_user_content = parent_comment.get("content", "")
        else:
            # 如果父评论还没有被缓存，尝试从评论内容中提取
            comment_text = comment_item.get("text", "")
            import re
            
            # 尝试从评论内容中提取被回复人昵称
            # 匹配 @用户名 的格式
            match = re.match(r'@([^@\s]+)', comment_text)
            if match:
                replied_user_nickname = match.group(1)
            else:
                # 匹配 "回复 @用户名:" 的格式
                match = re.search(r'回复\s*@([^@\s:]+)', comment_text)
                if match:
                    replied_user_nickname = match.group(1)
    avatar_info = (user_info.get("avatar_medium", {}) or user_info.get("avatar_300x300", {}) or user_info.get("avatar_168x168", {}) or user_info.get("avatar_thumb", {}) or {})
    # 兼容多种字段判断是否作者已赞该评论
    possible_keys = [
        "is_content_author_digg",
        "is_author_digg",
        "aweme_owner_digg",
        "author_digg",
        "aweme_author_digg",
        "is_aweme_author_digg",
        "is_comment_author_digg",
        "is_note_author_digg",
    ]
    _author_digg_val = 0
    for _k in possible_keys:
        if _k in comment_item:
            try:
                _author_digg_val = int(bool(comment_item.get(_k)))
                if _author_digg_val:
                    break
            except Exception:
                pass
    # 兜底：模糊匹配包含 author/owner 与 digg/like 的键
    if not _author_digg_val:
        for _k, _v in comment_item.items():
            if isinstance(_v, (int, bool)) and (
                ("author" in _k or "owner" in _k) and ("digg" in _k or "like" in _k)
            ):
                try:
                    if int(bool(_v)):
                        _author_digg_val = 1
                        break
                except Exception:
                    continue
    author_digg_mark = "是" if _author_digg_val else ""
    # 调整字段顺序与中文命名：评论时间、用户昵称、评论内容、点赞数、被回复人昵称、ip归属、评论图片、其余字段
    save_comment_item = {
        "评论时间": utils.get_time_str_from_unix_time(comment_item.get("create_time")),
        "用户昵称": user_info.get("nickname"),
        "评论内容": comment_item.get("text"),
        "点赞数": (comment_item.get("digg_count") if comment_item.get("digg_count") else 0),
        "被回复人昵称": replied_user_nickname,
        "被回复人原先的内容": replied_user_content,
        "作者已赞": author_digg_mark,
        "ip归属": comment_item.get("ip_label", ""),
        "评论图片": ",".join(_extract_comment_image_list(comment_item)),
        # 下面为附加信息，顺序随意，尽量中文
        "评论ID": comment_id,
        "视频ID": aweme_id,
        "用户ID": user_info.get("uid"),
        "sec_uid": user_info.get("sec_uid"),
        "短号": user_info.get("short_id"),
        "用户唯一ID": user_info.get("unique_id"),
        "用户签名": user_info.get("signature"),
        "头像": avatar_info.get("url_list", [""])[0],
        "子评论数": str(comment_item.get("reply_comment_total", 0)),
        "父评论ID": parent_comment_id,
        "最后更新时间": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.douyin.update_dy_aweme_comment] douyin aweme comment: {comment_id}, content: {save_comment_item.get('content')}")

    store = await DouyinStoreFactory.create_store()
    await store.store_comment(comment_item=save_comment_item)


async def save_creator(user_id: str, creator: Dict):
    user_info = creator.get("user", {})
    gender_map = {0: "未知", 1: "男", 2: "女"}
    avatar_uri = user_info.get("avatar_300x300", {}).get("uri")
    local_db_item = {
        "user_id": user_id,
        "nickname": user_info.get("nickname"),
        "gender": gender_map.get(user_info.get("gender"), "未知"),
        "avatar": f"https://p3-pc.douyinpic.com/img/{avatar_uri}" + r"~c5_300x300.jpeg?from=2956013662",
        "desc": user_info.get("signature"),
        "ip_location": user_info.get("ip_location"),
        "follows": user_info.get("following_count", 0),
        "fans": user_info.get("max_follower_count", 0),
        "interaction": user_info.get("total_favorited", 0),
        "videos_count": user_info.get("aweme_count", 0),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.douyin.save_creator] creator:{local_db_item}")
    store = await DouyinStoreFactory.create_store()
    await store.store_creator(local_db_item)


async def update_dy_aweme_image(aweme_id, pic_content, extension_file_name):
    """
    更新抖音笔记图片
    Args:
        aweme_id:
        pic_content:
        extension_file_name:

    Returns:

    """

    await DouYinImage().store_image({"aweme_id": aweme_id, "pic_content": pic_content, "extension_file_name": extension_file_name})


async def update_dy_aweme_video(aweme_id, video_content, extension_file_name):
    """
    更新抖音短视频
    Args:
        aweme_id:
        video_content:
        extension_file_name:

    Returns:

    """

    await DouYinVideo().store_video({"aweme_id": aweme_id, "video_content": video_content, "extension_file_name": extension_file_name})


async def clear_comment_cache():
    """
    清理评论缓存，在开始处理新视频时调用
    """
    global comment_cache, processed_comments
    comment_cache.clear()
    processed_comments.clear()
    utils.logger.info(f"[store.douyin.clear_comment_cache] 已清理评论缓存")


async def reset_store_factory():
    """
    重置存储工厂，在开始新的抓取任务时调用
    """
    DouyinStoreFactory._instance = None
    utils.logger.info(f"[store.douyin.reset_store_factory] 已重置存储工厂")


async def update_pending_reply_comments(aweme_id: str):
    """
    后处理函数：更新那些父评论ID存在但父评论信息已经缓存的回复评论
    """
    # 这里可以实现一个更复杂的逻辑来更新待处理的回复评论
    # 由于CSV存储的特性，我们无法直接更新已写入的行
    # 但我们可以记录日志，让用户知道哪些回复评论的父评论信息已经可用
    utils.logger.info(f"[store.douyin.update_pending_reply_comments] 当前缓存了 {len(comment_cache)} 条评论信息")
