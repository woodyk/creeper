#!/usr/bin/env python3
#
# plugins/parsers/beautifulsoup.py

import asyncio
from bs4 import BeautifulSoup

async def parse_page(html):
    soup = BeautifulSoup(html, 'lxml')
    return soup

class BeautifulSoupParser:
    async def parse(self, html):
        result = await parse_page(html)
        return result

beautifulsoup_parser = BeautifulSoupParser()
