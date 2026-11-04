#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""展示指定评论 CSV；未指定时，展示最近一次抓取的 CSV。"""

import argparse
import asyncio
from pathlib import Path

from store.douyin.douyin_web_store import DouyinWebStoreImplement
from tools.douyin_csv import CSV_OUTPUT_DIR, latest_comments_csv, read_comments_csv


async def start_web_with_auto_port(csv_path=None):
    """只导入选定的一个 CSV，启动对应的 report。"""
    web_store = None
    try:
        csv_path = Path(csv_path).resolve() if csv_path is not None else latest_comments_csv()
        if csv_path is None or not csv_path.is_file():
            print(f"❌ 未找到本轮评论 CSV，请先完成抓取。保存目录：{CSV_OUTPUT_DIR}")
            return False

        comments = read_comments_csv(csv_path)
        if not comments:
            print(f"⚠️ 本轮 CSV 没有评论，跳过 report：{csv_path}")
            return False

        print(f"📁 本次 report 只读取：{csv_path}")
        print(f"📊 本次导入 {len(comments)} 条评论")
        web_store = DouyinWebStoreImplement()
        await web_store.bulk_import_comments(comments, analyze_after=True)

        print(f"🌐 Report 已启动：http://localhost:{web_store.port}")
        print("📝 请访问本次打印的地址；按 Ctrl+C 停止服务器")
        while True:
            await asyncio.sleep(1)
    except Exception as error:
        print(f"❌ Report 启动失败：{error}")
        return False
    finally:
        if web_store is not None:
            web_store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="要展示的评论 CSV；默认展示最近一次抓取结果")
    args = parser.parse_args()
    try:
        asyncio.run(start_web_with_auto_port(args.csv))
    except KeyboardInterrupt:
        print("\n👋 Report 已停止")
