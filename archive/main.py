import sys
import asyncio
import json
import re
import config
from plugins.config import Config
from plugins.output import OutputPlugin
from plugins.connection_pool import ConnectionPool
from plugins.robots_txt import RobotsTxtPlugin
from plugins.parsers import LinkParser, ParserFactory
from plugins.middleware import MiddlewareInterface, SampleMiddleware

async def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: python main.py <URL>")
        exit(1)

    url = args[0]

    config = Config(user_agent="MyCustomUserAgent")
    connection_pool = ConnectionPool()
    crawler = CrawlerPlugin(config, OutputPlugin(), RobotsTxtPlugin(), connection_pool, [SampleMiddleware()])

    await crawler.run(url)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
