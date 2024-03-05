#!/usr/bin/env python3
#
# plugins/middlware/logging.py

import logging
import time

class LoggerMiddleware:
    async def __call__(self, handler):
        log_format = "%(asctime)s %(levelname)-8s %(message)s"
        logging.basicConfig(format=log_format, level=logging.INFO)

        start_time = time.monotonic()

        response = await handler(handler.request)

        elapsed_time = round(time.monotonic() - start_time, 3)
        logging.info(f"Request '{handler.request.url}' handled in {elapsed_time} seconds")

        return response

logger_middleware = LoggerMiddleware()
