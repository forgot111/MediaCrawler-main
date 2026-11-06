import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, call, patch
from playwright.async_api import Error as PlaywrightError

from media_platform.douyin.client import DouYinClient
from media_platform.douyin.core import DouYinCrawler
from media_platform.douyin.exception import DataFetchError
from store import douyin
from store.douyin.douyin_store_impl import DouyinCsvStoreImplement
from tools.douyin_csv import read_comments_csv


VIDEO = "7702770628012617706"


def item(cid, replies=0, **fields):
    return {"cid": cid, "reply_comment_total": replies, "text": "测试评论", "create_time": 1793743200, "user": {"nickname": "测试用户"}, **fields}


def page(items, more=0, cursor=0, **fields):
    return {"comments": items, "has_more": more, "cursor": cursor, "status_code": 0, **fields}


class CommentPaginationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = DouYinClient(headers={"User-Agent": "test"}, playwright_page=None, cookie_dict={})
        self.client.get_aweme_comments = AsyncMock()
        self.client.get_sub_comments = AsyncMock()
        self.saved = []
        self.sleep_patch = patch("media_platform.douyin.client.asyncio.sleep", new_callable=AsyncMock)
        self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

    async def collect(self, **options):
        async def save(video, comments):
            self.assertEqual(video, VIDEO)
            self.saved.extend(comments)

        settings = dict(crawl_interval=0, is_fetch_sub_comments=True, callback=save, max_count=4000, max_passes=1, max_retries=0)
        settings.update(options)
        return await self.client.get_aweme_all_comments(VIDEO, **settings)

    def summary(self):
        return self.client.comment_crawl_summaries[VIDEO]

    async def test_second_pass_adds_new_comments_without_rewriting_old_ids(self):
        self.client.get_aweme_comments.side_effect = [page([item("a", 1)]), page([item("a", 1), item("c")])]
        self.client.get_sub_comments.return_value = page([item("b")])
        result = await self.collect(max_passes=2)
        self.assertEqual([c["cid"] for c in result], ["a", "b", "c"])
        self.assertEqual([c["cid"] for c in self.saved], ["a", "b", "c"])
        self.assertEqual([p["added"] for p in self.summary()["passes"]], [2, 1])
        self.client.get_sub_comments.assert_awaited_once_with(VIDEO, "a", 0)

    async def test_transient_request_failure_retries_same_page(self):
        self.client.get_aweme_comments.side_effect = [DataFetchError("temporary failure"), page([item("a")])]
        self.assertEqual(len(await self.collect(max_retries=1)), 1)
        self.assertEqual(self.client.get_aweme_comments.await_args_list, [call(VIDEO, 0), call(VIDEO, 0)])
        self.assertEqual(self.summary()["retries"], 1)

    async def test_page_navigation_during_request_retries_same_cursor(self):
        self.client.get_aweme_comments.side_effect = [PlaywrightError("Execution context was destroyed, most likely because of a navigation"), page([item("a")])]
        self.assertEqual(len(await self.collect(max_retries=1)), 1)
        self.assertEqual(self.client.get_aweme_comments.await_args_list, [call(VIDEO, 0), call(VIDEO, 0)])
        self.assertEqual(self.summary()["retries"], 1)

    async def test_closed_browser_stops_additional_requests(self):
        self.client.get_aweme_comments.side_effect = PlaywrightError("Target page, context or browser has been closed")
        self.assertEqual(await self.collect(max_retries=3, max_passes=2), [])
        self.assertEqual(self.client.get_aweme_comments.await_count, 1)
        self.assertEqual(self.summary()["stop_reason"], "browser_unavailable")

    async def test_error_response_is_not_treated_as_end_of_comments(self):
        self.client.get_aweme_comments.side_effect = [{"status_code": 8}, page([item("a")])]
        self.assertEqual(len(await self.collect(max_retries=1)), 1)
        self.assertEqual(self.summary()["retries"], 1)

    async def test_missing_pagination_fields_are_retried(self):
        self.client.get_aweme_comments.side_effect = [{"status_code": 0}, page([item("a")])]
        self.assertEqual(len(await self.collect(max_retries=1)), 1)
        self.assertEqual(self.summary()["retries"], 1)

    async def test_empty_page_with_more_data_retries_then_advances(self):
        empty = page([], more=1, cursor=50)
        self.client.get_aweme_comments.side_effect = [empty, empty, page([item("a")])]
        self.assertEqual(len(await self.collect(max_retries=1)), 1)
        self.assertEqual(self.client.get_aweme_comments.await_args_list, [call(VIDEO, 0), call(VIDEO, 0), call(VIDEO, 50)])

    async def test_stuck_cursor_keeps_received_comments_and_stops(self):
        self.client.get_aweme_comments.return_value = page([item("a")], more=1, cursor=0)
        self.assertEqual(len(await self.collect()), 1)
        self.assertEqual(self.client.get_aweme_comments.await_count, 1)
        self.assertEqual(self.summary()["pages"][-1]["stop_reason"], "cursor_not_advancing")

    async def test_repeating_pages_cannot_loop_forever_with_advancing_cursors(self):
        self.client.get_aweme_comments.side_effect = [page([item("a")], more=1, cursor=n * 50) for n in range(1, 5)]
        self.assertEqual(len(await self.collect()), 1)
        self.assertEqual(self.client.get_aweme_comments.await_count, 4)
        self.assertEqual(self.summary()["pages"][-1]["stop_reason"], "repeated_pages")

    async def test_duplicates_do_not_consume_unique_comment_limit(self):
        self.client.get_aweme_comments.side_effect = [page([item("a"), item("b")], more=1, cursor=50), page([item("a"), item("c"), item("d")])]
        result = await self.collect(max_count=3)
        self.assertEqual([c["cid"] for c in result], ["a", "b", "c"])
        self.assertEqual(self.summary()["stop_reason"], "configured_limit")

    async def test_reply_failure_does_not_skip_other_reply_threads(self):
        self.client.get_aweme_comments.return_value = page([item("a", 1), item("b", 1)])

        async def replies(video, parent, cursor):
            if parent == "a":
                raise DataFetchError("temporary thread failure")
            return page([item("c")])

        self.client.get_sub_comments.side_effect = replies
        result = await self.collect(max_retries=1)
        self.assertEqual([c["cid"] for c in result], ["a", "b", "c"])
        self.assertEqual(self.summary()["incomplete_reply_threads"], [{"comment_id": "a", "expected": 1, "captured": 0}])
        self.assertEqual(self.summary()["failed_pages"], 1)

    async def test_reply_pagination_fetches_every_page(self):
        self.client.get_aweme_comments.return_value = page([item("a", 2)])
        self.client.get_sub_comments.side_effect = [page([item("b")], more=1, cursor=20), page([item("c")])]
        self.assertEqual(len(await self.collect()), 3)
        self.assertEqual(self.client.get_sub_comments.await_args_list, [call(VIDEO, "a", 0), call(VIDEO, "a", 20)])
        self.assertEqual(self.summary()["incomplete_reply_threads"], [])

    async def test_inline_replies_are_saved_and_deduplicated_against_reply_pages(self):
        self.client.get_aweme_comments.return_value = page([item("a", 2, reply_comment=[item("b")])])
        self.client.get_sub_comments.return_value = page([item("b"), item("c")])
        result = await self.collect()
        self.assertEqual([c["cid"] for c in result], ["a", "b", "c"])
        self.assertEqual(result[1]["reply_id"], "a")
        self.assertEqual(self.summary()["reply_comments"], 2)

    async def test_missing_video_id_is_filled_and_foreign_comments_are_rejected(self):
        self.client.get_aweme_comments.return_value = page([item("a", None), item("b", aweme_id=int(VIDEO)), item("foreign", aweme_id="other")])
        result = await self.collect()
        self.assertEqual([c["cid"] for c in result], ["a", "b"])
        self.assertTrue(all(c["aweme_id"] == VIDEO for c in result))
        self.assertEqual(self.summary()["invalid_comments_skipped"], 1)

    async def test_explicit_access_block_stops_additional_requests(self):
        self.client.get_aweme_comments.side_effect = DataFetchError("account blocked")
        self.assertEqual(await self.collect(max_retries=3, max_passes=2), [])
        self.assertEqual(self.client.get_aweme_comments.await_count, 1)
        self.assertEqual(self.summary()["stop_reason"], "access_blocked")

    async def test_comment_endpoints_use_the_requested_video_referer(self):
        client = DouYinClient(headers={"User-Agent": "test"}, playwright_page=None, cookie_dict={})
        client.get = AsyncMock(return_value=page([]))
        await client.get_aweme_comments(VIDEO, 50)
        await client.get_sub_comments(VIDEO, "a", 20)
        for request in client.get.await_args_list:
            self.assertEqual(request.kwargs["headers"]["Referer"], f"https://www.douyin.com/video/{VIDEO}")

    async def test_core_saves_actual_rows_and_diagnostics_for_same_run(self):
        self.client.get_aweme_comments.return_value = page([item("integration-parent", 1)])
        self.client.get_sub_comments.return_value = page([item("integration-reply")])
        crawler = DouYinCrawler()
        crawler.dy_client = self.client
        with tempfile.TemporaryDirectory() as directory:
            store = DouyinCsvStoreImplement()
            store.csv_store_path = directory
            await douyin.clear_comment_cache()
            with patch.object(douyin.DouyinStoreFactory, "create_store", new_callable=AsyncMock, return_value=store), patch("config.SAVE_DATA_OPTION", "csv"), patch("config.COMMENT_CRAWL_PASSES", 1), patch("config.COMMENT_CRAWL_INTERVAL", 0):
                await crawler.get_comments(VIDEO, asyncio.Semaphore(1))
            csv_path = Path(store.make_save_file_name("comments"))
            rows = read_comments_csv(csv_path)
            diagnostic = json.loads(csv_path.with_suffix(".crawl.json").read_text(encoding="utf-8"))
            self.assertEqual([c["评论ID"] for c in rows], ["integration-parent", "integration-reply"])
            self.assertEqual(rows[1]["父评论ID"], "integration-parent")
            self.assertEqual(diagnostic["videos"][VIDEO]["unique_comments"], len(rows))
            self.assertEqual(diagnostic["videos"][VIDEO]["top_level_comments"], 1)
            self.assertEqual(diagnostic["videos"][VIDEO]["reply_comments"], 1)


if __name__ == "__main__":
    unittest.main()
