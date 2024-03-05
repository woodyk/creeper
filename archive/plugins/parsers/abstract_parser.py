#!/usr/bin/env python3
#
# plugins/parsers/abstract_parser.py

class AbstractParser:
    async def parse(self, html):
        raise NotImplementedError("AbstractParser.parse method must be implemented in subclasses")

