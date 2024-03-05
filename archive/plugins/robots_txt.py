#!/usr/bin/env python3
#
# plugins/robots_txt.py

import aiohttp
import re

async def read_file(file_path):
    async with aiofiles.open(file_path, mode='rb') as f:
        return (await f.read())

class RobotsTxtPlugin:
    async def check(self, url):
        base_url = url[:url.rfind("/")]
        robots_txt_url = f"{base_url}/robots.txt"

        async with aiohttp.ClientSession() as session:
            raw_content = await read_file(robots_txt_url)
            content = raw_content.decode("utf-8")

        rules = []
        for rule in content.split("\n"):
            if len(rule) > 0 and not rule.startswith("#"):
                parsed_rule = rule.strip().split(":")
                if len(parsed_rule) >= 2:
                    directive, path_or_regex = parsed_rule
                    rules.append((directive, re.compile(path_or_regex)))

        return rules

robotstxt_plugin = RobotsTxtPlugin()
