#!/usr/bin/env python3
#
# tests/test_crawler.py

import unittest
import asyncio
from unittest.mock import MagicMock, patch
from plugins.output import OutputPlugin
from plugins.config import Config
from plugins.connection_pool import ConnectionPool
from plugins.robots_txt import RobotsTxtPlugin
from plugins.parsers.beautifulsoup import BeautifulSoupParser
from plugins.middleware.logger import LoggerMiddleware
from plugins.middleware.rate_limiter import RateLimiterMiddleware
from creeper.crawler import CrawlerPlugin

class TestCrawler(unittest.TestCase):
    @patch('creeper.crawler.plugins.output', new_creator=lambda: OutputPlugin())
    @patch('creeper.crawler.plugins.config', new_creator=lambda: Config())
    @patch('creeper.crawler.plugins.connection_pool', new_creator=lambda: ConnectionPool())
    @patch('creeper.crawler.plugins.parsers.beautifulsoup', new_creator=lambda: BeautifulSoupParser())
    @patch('creeper.crawler.plugins.middleware.logger', new_creator=lambda: LoggerMiddleware())
    @patch('creeper.crawler.plugins.middleware.rate_limiter', new_creator=lambda: RateLimiterMiddleware())
    @patch('creeper.crawler.plugins.robots_txt', new_creator=lambda: RobotsTxtPlugin())
    async def test_crawler(self, mock_robots_txt, mock_rate_limiter, mock_logger, mock_parser, mock_connection_pool, mock_config, mock_output):
        url = "https://wadih.com/"
        expected_rules = ["Rule 1", "Rule 2"]
        mock_robots_txt.return_value.__aenter__.return_value = {"Users-agent": expected_rules}

        crawler = CrawlerPlugin(mock_config, mock_output, mock_robots_txt, mock_connection_pool, [mock_logger, mock_rate_limiter])

        result = await crawler.run(url)

        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)
        self.assertTrue("status" in result)
        self.assertTrue("data" in result)
        self.assertEqual(result["status"], 200)

if __name__ == '__main__':
    unittest.main()
