#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取抖音评论，保存独立 CSV，再展示本轮抓取的 report。"""

import asyncio
from pathlib import Path

import config
from media_platform.douyin.core import DouYinCrawler
from start_web_auto_port import start_web_with_auto_port
from store.douyin import DouyinStoreFactory
from tools import utils
from tools.douyin_csv import CSV_OUTPUT_DIR


async def main():
    if config.SAVE_DATA_OPTION != "csv":
        utils.logger.error('完整流程需要 config/base_config.py 中 SAVE_DATA_OPTION = "csv"')
        return

    print("🎯 抖音评论抓取和 report")
    print(f"📁 CSV 保存目录：{CSV_OUTPUT_DIR}")
    print(f"🎬 目标视频：{', '.join(config.DY_SPECIFIED_ID_LIST)}")
    crawler = DouYinCrawler()
    try:
        utils.logger.info("🚀 阶段1：登录并抓取本轮评论")
        try:
            # start() 内部已经完成抓取，不能再次调用 get_specified_awemes()。
            await crawler.start()
        finally:
            if getattr(crawler, "browser_context", None) is not None:
                try:
                    await crawler.close()
                except Exception as close_error:
                    utils.logger.warning(f"关闭浏览器时出现错误：{close_error}")

        store = await DouyinStoreFactory.create_store()
        csv_path = Path(store.make_save_file_name("comments"))
        if not csv_path.is_file():
            utils.logger.warning("本轮没有生成评论 CSV，跳过 report。请检查抓取日志。")
            return

        print(f"✅ 本轮评论 CSV：{csv_path}")
        utils.logger.info("🌐 阶段2：只展示本轮评论")
        await start_web_with_auto_port(csv_path)
    except Exception:
        utils.logger.exception("❌ 本轮抓取失败，未载入历史 CSV")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已停止")
