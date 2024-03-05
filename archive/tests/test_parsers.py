#!/usr/bin/env python3
#
# tests/test_parsers.py

import unittest
import asyncio
from unittest.mock import MagicMock, patch
from plugins.parsers.abstract import AbstractParser
from plugins.parsers.beautifulsoup import BeautifulSoupParser

class TestBeautifulSoupParser(unittest.TestCase):
    @patch('plugins.parsers.beautifulsoup.parse_page')
    async def test_parse(self, mock_parse_page):
        html = "<html><body><div>Hello World</div></body></html>"
        parser = BeautifulSoupParser()

        result = await parser.parse(html)

        self.assertIsInstance(result, bs4.BeautifulSoup)
        self.assertEqual(str(result.html), html)

if __name__ == '__main__':
    unittest.main()
