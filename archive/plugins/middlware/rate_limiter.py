#!/usr/bin/env python3
#
# plugins/middlware/rate_limiter.py

import time
import random

class RateLimiterMiddleware:
    def __init__(self, limit=10, interval=1):
        self.limit = limit
        self.interval = interval
        self.last_request = {}

    async def __call__(self, handler):
        url = handler.request.url

        if url not in self.last_request or \
           ((time.monotonic() - self.last_request[url][0]) > self.interval):
            self.last_request[url] = (time.monotonic(), True)

            response = await handler(handler.request)

        else:
            response = self.last_request[url][1]

        return response

rate_limiter_middleware = RateLimiterMiddleware()
