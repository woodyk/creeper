#!/usr/bin/env python3
#
# terminal_gui.py

import os
import asyncio
import click
import rich
from rich.console import Console
from rich.progress import track
from rich.table import Table
from rich.panel import Panel
from textual.application import Application, Component
from textual.widgets import Widget, Border, BoxLayout, ScrollableFrame
from textual.containers import Container
from plugins.crawler import CrawlerPlugin

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
            await crawler.start(url)

        await self.enter_event_loop()

if __name__ == "__main__":
    MyTextualApp().run()
