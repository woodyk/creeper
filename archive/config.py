#!/usr/bin/env python3
#
# config.py

import re

class Config:
    def __init__(self, max_depth=-1, num_threads=5, user_agent="", exclusions=[], output_format="json"):
        self.max_depth = max_depth
        self.num_threads = num_threads
        self.user_agent = user_agent
        self.output_format = output_format
        self.exclusions = exclusions

class ExclusionFilters:
    def __init__(self, filters):
        self.filters = filters or []

class ExclusionFilter:
    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, url):
        return bool(re.search(self.pattern, url))
