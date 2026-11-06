# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import copy
import json
import urllib.parse
from typing import Any, Callable, Dict, Union, Optional

import httpx
from playwright.async_api import BrowserContext, Error as PlaywrightError

from base.base_crawler import AbstractApiClient
from tools import utils
from var import request_keyword_var

from .exception import *
from .field import *
from .help import *


class DouYinClient(AbstractApiClient):

    def __init__(
        self,
        timeout=60,  # 若开启爬取媒体选项，抖音的短视频需要更久的超时时间
        proxy=None,
        *,
        headers: Dict,
        playwright_page: Optional[Page],
        cookie_dict: Dict,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.douyin.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.comment_crawl_summaries: Dict[str, Dict] = {}

    async def __process_req_params(
        self,
        uri: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        request_method="GET",
    ):

        if not params:
            return
        headers = headers or self.headers
        local_storage: Dict = await self.playwright_page.evaluate("() => window.localStorage")  # type: ignore
        common_params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "version_code": "190600",
            "version_name": "19.6.0",
            "update_version_code": "170400",
            "pc_client_type": "1",
            "cookie_enabled": "true",
            "browser_language": "zh-CN",
            "browser_platform": "MacIntel",
            "browser_name": "Chrome",
            "browser_version": "125.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "os_name": "Mac OS",
            "os_version": "10.15.7",
            "cpu_core_num": "8",
            "device_memory": "8",
            "engine_version": "109.0",
            "platform": "PC",
            "screen_width": "2560",
            "screen_height": "1440",
            'effective_type': '4g',
            "round_trip_time": "50",
            "webid": get_web_id(),
            "msToken": local_storage.get("xmst"),
        }
        params.update(common_params)
        query_string = urllib.parse.urlencode(params)

        # 20240927 a-bogus更新（JS版本）
        post_data = {}
        if request_method == "POST":
            post_data = params
        a_bogus = await get_a_bogus(uri, query_string, post_data, headers["User-Agent"], self.playwright_page)
        params["a_bogus"] = a_bogus

    async def request(self, method, url, **kwargs):
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
        try:
            if response.text == "" or response.text == "blocked":
                utils.logger.error(f"request params incrr, response.text: {response.text}")
                raise Exception("account blocked")
            return response.json()
        except Exception as e:
            raise DataFetchError(f"{e}, {response.text}")

    async def get(self, uri: str, params: Optional[Dict] = None, headers: Optional[Dict] = None):
        """
        GET请求
        """
        await self.__process_req_params(uri, params, headers)
        headers = headers or self.headers
        return await self.request(method="GET", url=f"{self._host}{uri}", params=params, headers=headers)

    async def post(self, uri: str, data: dict, headers: Optional[Dict] = None):
        await self.__process_req_params(uri, data, headers)
        headers = headers or self.headers
        return await self.request(method="POST", url=f"{self._host}{uri}", data=data, headers=headers)

    async def pong(self, browser_context: BrowserContext) -> bool:
        local_storage = await self.playwright_page.evaluate("() => window.localStorage")
        if local_storage.get("HasUserLogin", "") == "1":
            return True

        _, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        return cookie_dict.get("LOGIN_STATUS") == "1"

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def search_info_by_keyword(
        self,
        keyword: str,
        offset: int = 0,
        search_channel: SearchChannelType = SearchChannelType.GENERAL,
        sort_type: SearchSortType = SearchSortType.GENERAL,
        publish_time: PublishTimeType = PublishTimeType.UNLIMITED,
        search_id: str = "",
    ):
        """
        DouYin Web Search API
        :param keyword:
        :param offset:
        :param search_channel:
        :param sort_type:
        :param publish_time: ·
        :param search_id: ·
        :return:
        """
        query_params = {
            'search_channel': search_channel.value,
            'enable_history': '1',
            'keyword': keyword,
            'search_source': 'tab_search',
            'query_correct_type': '1',
            'is_filter_search': '0',
            'from_group_id': '7378810571505847586',
            'offset': offset,
            'count': '15',
            'need_filter_settings': '1',
            'list_type': 'multi',
            'search_id': search_id,
        }
        if sort_type.value != SearchSortType.GENERAL.value or publish_time.value != PublishTimeType.UNLIMITED.value:
            query_params["filter_selected"] = json.dumps({"sort_type": str(sort_type.value), "publish_time": str(publish_time.value)})
            query_params["is_filter_search"] = 1
            query_params["search_source"] = "tab_search"
        referer_url = f"https://www.douyin.com/search/{keyword}?aid=f594bbd9-a0e2-4651-9319-ebe3cb6298c1&type=general"
        headers = copy.copy(self.headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=':/')
        return await self.get("/aweme/v1/web/general/search/single/", query_params, headers=headers)

    async def get_video_by_id(self, aweme_id: str) -> Any:
        """
        DouYin Video Detail API
        :param aweme_id:
        :return:
        """
        params = {"aweme_id": aweme_id}
        headers = copy.copy(self.headers)
        del headers["Origin"]
        res = await self.get("/aweme/v1/web/aweme/detail/", params, headers)
        return res.get("aweme_detail", {})

    async def get_aweme_comments(self, aweme_id: str, cursor: int = 0):
        """get note comments

        """
        uri = "/aweme/v1/web/comment/list/"
        params = {"aweme_id": aweme_id, "cursor": cursor, "count": 50, "item_type": 0}
        headers = copy.copy(self.headers)
        headers["Referer"] = f"https://www.douyin.com/video/{aweme_id}"
        return await self.get(uri, params, headers=headers)

    async def get_sub_comments(self, aweme_id: str, comment_id: str, cursor: int = 0):
        """
            获取子评论
        """
        uri = "/aweme/v1/web/comment/list/reply/"
        params = {
            'comment_id': comment_id,
            "cursor": cursor,
            "count": 20,
            "item_type": 0,
            "item_id": aweme_id,
        }
        headers = copy.copy(self.headers)
        headers["Referer"] = f"https://www.douyin.com/video/{aweme_id}"
        return await self.get(uri, params, headers=headers)

    async def _request_comment_page(self, fetch, cursor, label, retries, interval, summary):
        """对同一页作有限重试，异常响应不能被当成评论已读完。"""
        for attempt in range(retries + 1):
            summary["requests"] += 1
            try:
                page = await fetch(cursor)
                if not isinstance(page, dict) or page.get("status_code", 0) not in (0, "0"):
                    raise DataFetchError("评论接口返回非成功状态")
                if "comments" not in page or "has_more" not in page:
                    raise DataFetchError("评论接口缺少 comments 或 has_more 字段")
                if page["comments"] is not None and not isinstance(page["comments"], list):
                    raise DataFetchError("评论列表格式无效")
                more = page["has_more"] in (True, 1, "1", "true")
                if more and ("cursor" not in page or not str(page["cursor"]).isdigit()):
                    raise DataFetchError("评论接口缺少有效的下一页游标")
                # 空页但仍有下一页时，先重试原页，再按返回的游标继续。
                if not page["comments"] and more and attempt < retries:
                    raise DataFetchError("接口暂时返回空页，但 has_more=1")
                return page
            except (httpx.RequestError, httpx.HTTPStatusError, PlaywrightError) as error:
                if isinstance(error, PlaywrightError) and not any(
                    text in str(error) for text in ("Execution context was destroyed", "Cannot find context")
                ):
                    summary["stop_reason"] = "browser_unavailable"
                    summary["warnings"].append({"stage": label, "cursor": cursor, "reason": "browser_unavailable"})
                    return None
                if isinstance(error, IPBlockError) or "account blocked" in str(error):
                    summary["stop_reason"] = "access_blocked"
                    summary["warnings"].append({"stage": label, "cursor": cursor, "reason": "access_blocked"})
                    return None
                if attempt == retries:
                    summary["failed_pages"] += 1
                    summary["warnings"].append({"stage": label, "cursor": cursor, "reason": "request_failed"})
                    utils.logger.warning(f"[DouYinClient] {label} cursor={cursor} 重试后仍失败：{type(error).__name__}")
                    return None
                summary["retries"] += 1
                utils.logger.warning(f"[DouYinClient] {label} cursor={cursor} 暂未成功，稍后重试 {attempt + 1}/{retries}")
                await asyncio.sleep(max(1.0, interval) * (2 ** attempt))

    async def get_aweme_all_comments(
        self,
        aweme_id: str,
        crawl_interval: float = 1.0,
        is_fetch_sub_comments=False,
        callback: Optional[Callable] = None,
        max_count: int = 10,
        max_passes: int = 2,
        max_retries: int = 3,
    ):
        """分页抓取并在本轮任务内补抓，max_count 按唯一评论（含回复）计数。"""
        aweme_id = str(aweme_id)
        max_count = max(0, int(max_count))
        max_passes = max(1, int(max_passes))
        max_retries = max(0, int(max_retries))
        crawl_interval = max(0.0, float(crawl_interval))
        result, seen, roots, thread_ids = [], set(), {}, {}
        summary = {
            "video_id": aweme_id,
            "max_count": max_count,
            "requested_passes": max_passes,
            "requests": 0,
            "retries": 0,
            "failed_pages": 0,
            "duplicates_skipped": 0,
            "invalid_comments_skipped": 0,
            "api_totals": [],
            "passes": [],
            "pages": [],
            "warnings": [],
            "stop_reason": "max_passes",
        }
        self.comment_crawl_summaries[aweme_id] = summary
        current_pass = 0

        def count(value):
            try:
                return max(0, int(value or 0))
            except (ValueError, TypeError):
                return 0

        async def accept(items, parent_id=None):
            fresh = []
            for raw in items:
                if not isinstance(raw, dict) or raw.get("cid") in (None, ""):
                    summary["invalid_comments_skipped"] += 1
                    continue
                if raw.get("aweme_id") not in (None, "") and str(raw["aweme_id"]) != aweme_id:
                    summary["invalid_comments_skipped"] += 1
                    continue
                item = dict(raw)
                cid = str(item["cid"])
                item["cid"], item["aweme_id"] = cid, aweme_id
                if item.get("reply_id") in (None, "", 0, "0"):
                    item["reply_id"] = parent_id or "0"
                else:
                    item["reply_id"] = str(item["reply_id"])
                if cid in seen:
                    summary["duplicates_skipped"] += 1
                    if parent_id is None and cid in roots:
                        roots[cid] = item
                    if parent_id is not None:
                        thread_ids.setdefault(parent_id, set()).add(cid)
                    continue
                if len(result) + len(fresh) >= max_count:
                    break
                seen.add(cid)
                fresh.append(item)
                if parent_id is None:
                    roots[cid] = item
                else:
                    thread_ids.setdefault(parent_id, set()).add(cid)
            if fresh:
                if callback:
                    await callback(aweme_id, fresh)
                result.extend(fresh)
            return len(fresh)

        async def collect_pages(fetch, parent_id=None):
            cursor, visited, empty_pages = 0, set(), 0
            stream_ids, repeated_pages = set(), 0
            label = f"回复 {parent_id}" if parent_id is not None else "一级评论"
            while len(result) < max_count:
                if summary["requests"]:
                    await asyncio.sleep(crawl_interval)
                page = await self._request_comment_page(
                    fetch, cursor, label, max_retries, crawl_interval, summary
                )
                if page is None:
                    return
                visited.add(cursor)
                items = page.get("comments") or []
                page_ids = {str(item["cid"]) for item in items if isinstance(item, dict) and item.get("cid") is not None}
                repeated_pages = 0 if page_ids - stream_ids else repeated_pages + 1
                stream_ids.update(page_ids)
                added = await accept(items, parent_id)
                more = page["has_more"] in (True, 1, "1", "true")
                next_cursor = count(page.get("cursor"))
                record = {
                    "pass": current_pass, "stage": label, "cursor": cursor,
                    "next_cursor": next_cursor, "has_more": more,
                    "returned": len(items), "added": added,
                }
                summary["pages"].append(record)
                if parent_id is None and page.get("total") is not None:
                    total = count(page["total"])
                    if total not in summary["api_totals"]:
                        summary["api_totals"].append(total)
                if len(result) >= max_count:
                    record["stop_reason"] = "configured_limit"
                    return
                if not more:
                    record["stop_reason"] = "api_has_more_0"
                    return
                if next_cursor in visited:
                    record["stop_reason"] = "cursor_not_advancing"
                    summary["warnings"].append({"stage": label, "cursor": cursor, "reason": "cursor_not_advancing"})
                    return
                empty_pages = empty_pages + 1 if not items else 0
                if empty_pages >= 3:
                    record["stop_reason"] = "consecutive_empty_pages"
                    summary["warnings"].append({"stage": label, "cursor": cursor, "reason": "consecutive_empty_pages"})
                    return
                if items and repeated_pages >= 3:
                    record["stop_reason"] = "repeated_pages"
                    summary["warnings"].append({"stage": label, "cursor": cursor, "reason": "repeated_pages"})
                    return
                cursor = next_cursor

        try:
            for current_pass in range(1, max_passes + 1):
                before = len(result)
                await collect_pages(lambda cursor: self.get_aweme_comments(aweme_id, cursor))
                if summary["stop_reason"] in ("access_blocked", "browser_unavailable"):
                    break
                if is_fetch_sub_comments:
                    for parent_id, item in list(roots.items()):
                        if len(result) >= max_count or summary["stop_reason"] in ("access_blocked", "browser_unavailable"):
                            break
                        embedded = item.get("reply_comment") or []
                        if isinstance(embedded, list):
                            await accept(embedded, parent_id)
                        expected = count(item.get("reply_comment_total"))
                        if expected > len(thread_ids.get(parent_id, set())):
                            await collect_pages(
                                lambda cursor, cid=parent_id: self.get_sub_comments(aweme_id, cid, cursor),
                                parent_id,
                            )
                added = len(result) - before
                summary["passes"].append({"pass": current_pass, "added": added, "total": len(result)})
                utils.logger.info(f"[DouYinClient] 视频 {aweme_id} 第 {current_pass} 轮新增 {added} 条，累计 {len(result)} 条唯一评论")
                if summary["stop_reason"] in ("access_blocked", "browser_unavailable"):
                    break
                if len(result) >= max_count:
                    summary["stop_reason"] = "configured_limit"
                    break
                if current_pass > 1 and not added:
                    summary["stop_reason"] = "no_new_comments"
                    break
        finally:
            summary["unique_comments"] = len(result)
            summary["top_level_comments"] = len(roots)
            summary["reply_comments"] = len(result) - len(roots)
            summary["incomplete_reply_threads"] = [
                {"comment_id": cid, "expected": count(item.get("reply_comment_total")),
                 "captured": len(thread_ids.get(cid, set()))}
                for cid, item in roots.items()
                if is_fetch_sub_comments and count(item.get("reply_comment_total")) > len(thread_ids.get(cid, set()))
            ]
        utils.logger.info(
            f"[DouYinClient] 视频 {aweme_id}：一级 {summary['top_level_comments']} 条，"
            f"回复 {summary['reply_comments']} 条，共 {len(result)} 条；停止原因：{summary['stop_reason']}"
        )
        if summary["warnings"] or summary["incomplete_reply_threads"]:
            utils.logger.warning("[DouYinClient] 存在分页异常或未取齐的回复，请查看本轮 .crawl.json 诊断文件")
        return result

    async def get_user_info(self, sec_user_id: str):
        uri = "/aweme/v1/web/user/profile/other/"
        params = {
            "sec_user_id": sec_user_id,
            "publish_video_strategy_type": 2,
            "personal_center_strategy": 1,
        }
        return await self.get(uri, params)

    async def get_user_aweme_posts(self, sec_user_id: str, max_cursor: str = "") -> Dict:
        uri = "/aweme/v1/web/aweme/post/"
        params = {
            "sec_user_id": sec_user_id,
            "count": 18,
            "max_cursor": max_cursor,
            "locate_query": "false",
            "publish_video_strategy_type": 2,
            'verifyFp': 'verify_ma3hrt8n_q2q2HyYA_uLyO_4N6D_BLvX_E2LgoGmkA1BU',
            'fp': 'verify_ma3hrt8n_q2q2HyYA_uLyO_4N6D_BLvX_E2LgoGmkA1BU'
        }
        return await self.get(uri, params)

    async def get_all_user_aweme_posts(self, sec_user_id: str, callback: Optional[Callable] = None):
        posts_has_more = 1
        max_cursor = ""
        result = []
        while posts_has_more == 1:
            aweme_post_res = await self.get_user_aweme_posts(sec_user_id, max_cursor)
            posts_has_more = aweme_post_res.get("has_more", 0)
            max_cursor = aweme_post_res.get("max_cursor")
            aweme_list = aweme_post_res.get("aweme_list") if aweme_post_res.get("aweme_list") else []
            utils.logger.info(f"[DouYinClient.get_all_user_aweme_posts] get sec_user_id:{sec_user_id} video len : {len(aweme_list)}")
            if callback:
                await callback(aweme_list)
            result.extend(aweme_list)
        return result

    async def get_aweme_media(self, url: str) -> Union[bytes, None]:
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            try:
                response = await client.request("GET", url, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                if not response.reason_phrase == "OK":
                    utils.logger.error(f"[DouYinClient.get_aweme_media] request {url} err, res:{response.text}")
                    return None
                else:
                    return response.content
            except httpx.HTTPError as exc:  # some wrong when call httpx.request method, such as connection error, client error, server error or response status code is not 2xx
                utils.logger.error(f"[DouYinClient.get_aweme_media] {exc.__class__.__name__} for {exc.request.url} - {exc}")  # 保留原始异常类型名称，以便开发者调试
                return None
