import asyncio
import sys
from typing import Optional

import config
from base.base_crawler import AbstractCrawler
from media_platform.douyin import DouYinCrawler


class CrawlerFactory:
    CRAWLERS = {
        "dy": DouYinCrawler,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError(
                "Invalid Media Platform Currently only supported dy (douyin) ..."
            )
        return crawler_class()


crawler: Optional[AbstractCrawler] = None


async def main():
    # Init crawler
    global crawler

    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.start()


def cleanup():
    if crawler:
        # asyncio.run(crawler.close())
        pass


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    finally:
        cleanup()
