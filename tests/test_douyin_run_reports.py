import asyncio
import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.request import urlopen

import start_douyin_complete as complete
import start_web_auto_port as report
from store import douyin
from store.douyin.douyin_store_impl import DouyinCsvStoreImplement
from store.douyin.douyin_web_store import DouyinWebStoreImplement
from tools import douyin_csv


def comment(comment_id, text, likes=1):
    return {
        "评论ID": comment_id,
        "视频ID": "7702770628012617706",
        "用户ID": "000123",
        "父评论ID": "",
        "评论内容": text,
        "评论时间": "2026-11-03 10:00:00",
        "用户昵称": "测试用户",
        "点赞数": likes,
        "子评论数": 0,
    }


class RunReportsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path_patch = patch.object(DouyinCsvStoreImplement, "csv_store_path", str(self.root / "csv"))
        self.path_patch.start()
        self.original_store = douyin.DouyinStoreFactory._instance
        self.addCleanup(self.path_patch.stop)
        self.addCleanup(self.temp.cleanup)

    async def asyncTearDown(self):
        douyin.DouyinStoreFactory._instance = self.original_store

    async def test_same_video_is_saved_separately_for_each_crawl(self):
        first = DouyinCsvStoreImplement()
        await asyncio.gather(
            first.store_comment(comment("100", "第一轮评论一")),
            first.store_comment(comment("101", "第一轮评论二")),
        )
        second = DouyinCsvStoreImplement()
        await second.store_comment(comment("200", "第二轮评论"))

        first_path = Path(first.make_save_file_name("comments"))
        second_path = Path(second.make_save_file_name("comments"))
        self.assertNotEqual(first_path, second_path)
        self.assertEqual({c["评论ID"] for c in douyin_csv.read_comments_csv(first_path)}, {"100", "101"})
        self.assertEqual([c["评论ID"] for c in douyin_csv.read_comments_csv(second_path)], ["200"])

    async def test_import_preserves_large_ids_and_quoted_multiline_comments(self):
        store = DouyinCsvStoreImplement()
        item = comment("7702770628012617707", '中文评论,含逗号\n和"引号"', 7)
        item["父评论ID"] = "7702770628012617708"
        await store.store_comment(item)
        loaded = douyin_csv.read_comments_csv(Path(store.make_save_file_name("comments")))[0]
        self.assertEqual(loaded["评论ID"], item["评论ID"])
        self.assertEqual(loaded["视频ID"], item["视频ID"])
        self.assertEqual(loaded["父评论ID"], item["父评论ID"])
        self.assertEqual(loaded["用户ID"], "000123")
        self.assertEqual(loaded["评论内容"], item["评论内容"])
        self.assertEqual(loaded["点赞数"], 7)

    async def test_standalone_report_selects_newest_csv_with_legacy_fallback(self):
        new_dir = self.root / "csv"
        legacy_dir = self.root / "legacy"
        new_dir.mkdir()
        legacy_dir.mkdir()
        old = new_dir / "z_old_comments.csv"
        latest = new_dir / "a_latest_comments.csv"
        legacy = legacy_dir / "legacy_comments.csv"
        for path in (old, latest, legacy):
            path.touch()
        os.utime(old, ns=(1, 1))
        os.utime(latest, ns=(2, 2))
        with patch.object(douyin_csv, "CSV_OUTPUT_DIR", new_dir), patch.object(douyin_csv, "LEGACY_CSV_DIR", legacy_dir):
            self.assertEqual(douyin_csv.latest_comments_csv(), latest)
            old.unlink()
            latest.unlink()
            self.assertEqual(douyin_csv.latest_comments_csv(), legacy)

    async def test_complete_flow_crawls_once_and_passes_exact_current_csv(self):
        old = DouyinCsvStoreImplement()
        await old.store_comment(comment("100", "上轮评论"))
        crawler = AsyncMock()
        crawler.browser_context = object()

        async def crawl():
            await douyin.reset_store_factory()
            store = await douyin.DouyinStoreFactory.create_store()
            await store.store_comment(comment("200", "本轮评论"))

        crawler.start.side_effect = crawl
        with patch.object(complete.config, "SAVE_DATA_OPTION", "csv"), patch.object(complete, "DouYinCrawler", return_value=crawler), patch.object(complete, "start_web_with_auto_port", new_callable=AsyncMock) as show_report:
            await complete.main()
            crawler.start.assert_awaited_once()
            crawler.get_specified_awemes.assert_not_awaited()
            crawler.close.assert_awaited_once()
            show_report.assert_awaited_once()
            current_path = show_report.await_args.args[0]

        self.assertNotEqual(current_path, Path(old.make_save_file_name("comments")))
        self.assertEqual([c["评论ID"] for c in douyin_csv.read_comments_csv(current_path)], ["200"])
        self.assertEqual([c["评论ID"] for c in douyin_csv.read_comments_csv(Path(old.make_save_file_name("comments")))], ["100"])

    async def test_empty_crawl_does_not_reuse_previous_csv(self):
        old = DouyinCsvStoreImplement()
        await old.store_comment(comment("100", "上轮评论"))
        douyin.DouyinStoreFactory._instance = old
        crawler = AsyncMock()
        crawler.browser_context = object()
        crawler.start.side_effect = douyin.reset_store_factory
        with patch.object(complete.config, "SAVE_DATA_OPTION", "csv"), patch.object(complete, "DouYinCrawler", return_value=crawler), patch.object(complete, "start_web_with_auto_port", new_callable=AsyncMock) as show_report:
            await complete.main()
            show_report.assert_not_awaited()
        self.assertTrue(Path(old.make_save_file_name("comments")).is_file())

    async def test_failed_crawl_does_not_open_report(self):
        crawler = AsyncMock()
        crawler.browser_context = object()
        crawler.start.side_effect = RuntimeError("模拟抓取失败")
        with patch.object(complete.config, "SAVE_DATA_OPTION", "csv"), patch.object(complete, "DouYinCrawler", return_value=crawler), patch.object(complete, "start_web_with_auto_port", new_callable=AsyncMock) as show_report:
            with self.assertLogs("MediaCrawler", level="ERROR"):
                await complete.main()
            show_report.assert_not_awaited()

    async def test_missing_explicit_csv_never_falls_back_to_history(self):
        with patch.object(report, "latest_comments_csv") as find_history, patch.object(report, "DouyinWebStoreImplement") as web_store:
            self.assertFalse(await report.start_web_with_auto_port(self.root / "missing_comments.csv"))
            find_history.assert_not_called()
            web_store.assert_not_called()

    async def test_http_report_contains_only_current_csv_and_keeps_workdir(self):
        cwd = Path.cwd()
        web_path = self.root / "web"
        web_path.mkdir()
        (web_path / "data.json").write_text('{"comments":[{"评论ID":"stale"}]}', encoding="utf-8")
        first = DouyinWebStoreImplement(port=0, web_path=web_path, open_browser=False)
        second = None
        try:
            await first.bulk_import_comments([comment("100", "第一轮评论")])
            # 请求同一端口，确认新 report 自动使用可用端口并服务自己的评论。
            second = DouyinWebStoreImplement(port=first.port, web_path=web_path, open_browser=False)
            await second.bulk_import_comments([comment("200", "本轮评论", 8)])
            self.assertNotEqual(first.port, second.port)
            self.assertEqual(Path.cwd(), cwd)

            with urlopen(f"http://127.0.0.1:{second.port}/data.json") as response:
                data = json.load(response)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual([c["评论ID"] for c in data["comments"]], ["200"])
            self.assertEqual(data["stats"]["total_comments"], 1)
            self.assertEqual(data["stats"]["total_likes"], 8)
            self.assertEqual(json.loads((web_path / "data.json").read_text(encoding="utf-8"))["comments"], data["comments"])

            with urlopen(f"http://127.0.0.1:{second.port}/") as response:
                self.assertIn('<html lang="zh-CN">', response.read().decode("utf-8"))
            with urlopen(f"http://127.0.0.1:{second.port}/export/csv") as response:
                exported = list(csv.DictReader(response.read().decode("utf-8-sig").splitlines()))
            self.assertEqual([c["评论ID"] for c in exported], ["200"])
        finally:
            await asyncio.to_thread(first.close)
            if second is not None:
                await asyncio.to_thread(second.close)


if __name__ == "__main__":
    unittest.main()
