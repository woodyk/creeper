#!/usr/bin/env python3
#
# crawler.py

import os
import sys
import asyncio
import aiohttp
import click
import rich
from rich.console import Console
from rich.progress import track
from rich.table import Table
from rich.panel import Panel
from plugins.crawler import CrawlerPlugin
import textual as t
from textual.widgets import ApplicationWindow, Label, Entry, Button
from textual.containers import Container, VerticalLayout
from textual.app import App

class CrawlerPlugin:
    # Add the implementation of the CrawlerPlugin here
    pass

class TextualApp(Application):
    title = "Creeper - Simple Web Crawler"

    def setup(self):
        self.crawlers = {}

class CrawlerWidget(Component):
    def render(self):
        table = Table(title="Crawler Status")
        table.add_column("Name", justify="left", style="cyan")
        table.add_column("Status", justify="center")

        self.update(lambda: table.rows)

        return ScrollableFrame(Table(table))

    async def on_mount(self, parent):
        self.parent = parent
        self.app = self.parent.app

        self.status = self.style.resolve("status.")

        self.table = self.render()
        self.parent.add(self.table)

        self.refresh()

    def refresh(self):
        rows = []
        for name, crawler in self.app.crawlers.items():
            status = "Running" if crawler.is_running else "Idle"
            rows.append([name, status])

        self.table.rows = rows

class MainScreen(Container):
    def __init__(self, app):
        super().__init__(app)
        self.add(CrawlerWidget())

class AppScreen(ScrollableFrame):
    def __init__(self, app):
        super().__init__(app)
        self.add(MainScreen(app))

class MyTextualApp(TextualApp):
    def configure_option_parser(self, parser):
        parser.add_argument("-u", "--urls", nargs="+", help="List of URLs to crawl")

    async def main(self):
        args = self.parse_args()

        console = Console()
        click.echo(console.strip)

        self.set_window_size(80, 50)
        self.set_theme("default")

        self.add(AppScreen(self))

        self.crawlers = {}

        for url in args.urls:
            crawler = CrawlerPlugin()
            self.crawlers[crawler.name] = crawler
            self.add_component(crawler)
            await self.spawn_crawler(crawler, url)

        await self.enter_event_loop()

    async def spawn_crawler(self, crawler, url):
        try:
            await crawler.start(url)
        except Exception as exc:
            print(f"An error occurred while crawling '{url}' ({exc}).")

        self.crawlers[crawler.name].is_running = False
        self.emit("crawler-finished", {"name": crawler.name})

class Crawler(object):
    _config = None

    @property
    def config(self):
        if not self._config:
            self._config = {
                "urls": [],
                "delay": 3,
                "max_concurrent": 5,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
            }
        return self._config

    async def run_crawlers(self):
        tasks = []
        self._spawned_crawlers = 0

        for url in self.config["urls"]:
            crawler = CrawlerPlugin()
            self.crawlers.append(crawler)
            tasks.append(self._spawn_crawler(crawler, url))

            self._spawned_crawlers += 1

            if len(tasks) >= self.config["max_concurrent"]:
                await self._wait_for_completed_task(tasks)

        await self._handle_results(tasks)

    async def _spawn_crawler(self, crawler, url):
        self.crawlers[-1] = crawler
        self.crawlers[-1].url = url
        self.crawlers[-1].is_running = True

        task = self.create_task(crawler.run(url))
        task.add_done_callback(lambda t: self._on_crawler_finished(t))

        return task

    async def _wait_for_completed_task(self, tasks):
        await asyncio.gather(*tasks)

    async def _handle_results(self, tasks):
        for future in tasks:
            result = await future
            if result is not None:
                data = result.result()
                self.emit("data-received", {"data": data})

    async def _on_crawler_finished(self, future):
        crawler = self.crawlers.pop(-1)
        self.crawlers[-1].is_running = False

if __name__ == "__main__":
    crawler = Crawler()
    asyncio.get_event_loop().run_until_complete(crawler.run_crawlers())
