#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# File: creeper.py
# Author: Wadih Khairallah
# Description: Optimized self-hosted web crawler with generic file downloads,
#              session-based output, and resumable sessions. All session state
#              (configuration, visited/unvisited, buffer, logs) is stored in the
#              session directory. To start a new session, supply the usual switches.
#              To resume an unfinished session, simply run:
#                  ./creeper.py <session_directory>
#
# Great sites for testing:
#   https://crawler-test.com/
#   https://books.toscrape.com
#

import argparse
import logging
import os
import re
import signal
import sys
import time
import hashlib
import json
import shutil
import random
import socket
from urllib.parse import urlparse, urljoin, urlunparse

import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch

# Optionally import Selenium if dynamic crawling is enabled
try:
    from selenium import webdriver
    from webdriver_manager.firefox import GeckoDriverManager
except ImportError:
    webdriver = None

# Clear any default logging configuration.
logging.getLogger().handlers = []
logger = logging.getLogger(__name__)
# Handlers will be added later based on verbosity.

# Filenames for session state stored in the session directory.
CONFIG_FILENAME = "config.json"
VISITED_FILENAME = "visited.txt"
UNVISITED_FILENAME = "unvisited.txt"
SESSION_JSON = "session.json"
SESSION_LOG = "session.log"
BUFFER_FILENAME = "session_buffer.ndjson"

# Define file categories and associated extensions.
FILE_CATEGORIES = {
    "doc":   [".pdf", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"],
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"],
    "audio": [".mp3", ".wav", ".ogg", ".flac", ".aac"],
    "video": [".mp4", ".avi", ".mkv", ".mov", ".webm"]
}

class WebCrawler:
    def __init__(self, config):
        # Load all session settings from config.
        self.config = config
        self.seed = config["seed"]
        self.seed_host = self.get_host(self.seed)
        self.follow = config.get("follow", False)
        self.preserve_path = config.get("preserve_path", False)
        self.download_docs = config.get("download_docs", False)
        self.download_images = config.get("download_images", False)
        self.download_audio = config.get("download_audio", False)
        self.download_video = config.get("download_video", False)
        self.all_files = config.get("all_files", False)
        self.dynamic = config.get("dynamic", False)
        self.es_host = config.get("es_host", None)
        self.verbose = config.get("verbose", 0)

        self.es = Elasticsearch(self.es_host) if self.es_host else None

        # The session output directory.
        self.output_dir = config["output_dir"]
        self.visited_file = os.path.join(self.output_dir, VISITED_FILENAME)
        self.unvisited_file = os.path.join(self.output_dir, UNVISITED_FILENAME)
        self.buffer_file = os.path.join(self.output_dir, BUFFER_FILENAME)

        self.visited = {}   # URL -> hash
        self.unvisited = {} # URL -> placeholder
        self.hash_vals = set()
        self.shutdown_flag = False
        self.session_results = []  # Collected crawl data

        # Create the output directory if necessary.
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Create subdirectories for file categories.
        self.download_dirs = {}
        for cat in FILE_CATEGORIES.keys():
            dir_path = os.path.join(self.output_dir, cat)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            self.download_dirs[cat] = dir_path

        # Configure logging: always log to session.log.
        file_handler = logging.FileHandler(os.path.join(self.output_dir, SESSION_LOG))
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(file_handler)
        if self.verbose > 0:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
        logger.info(f"Session output directory: {self.output_dir}")

        # Use a persistent requests session.
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'
        })

        # Initialize Selenium driver if dynamic crawling is enabled.
        self.driver = None
        if self.dynamic and webdriver:
            options = webdriver.FirefoxOptions()
            options.headless = True
            self.driver = webdriver.Firefox(
                service=webdriver.firefox.service.Service(GeckoDriverManager().install(), log_path=os.devnull),
                options=options
            )

        signal.signal(signal.SIGINT, self.handle_signal)

        # Load previously buffered crawl data (if any).
        self.load_buffer()

    def handle_signal(self, signum, frame):
        logger.info("Shutdown signal received.")
        self.shutdown_flag = True

    def save_config(self):
        config_path = os.path.join(self.output_dir, CONFIG_FILENAME)
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=4)
        logger.info(f"Session config saved to {config_path}")

    def load_state(self):
        if os.path.exists(self.visited_file):
            with open(self.visited_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if "<:>" in line:
                        h, url = line.split("<:>", 1)
                        self.visited[url] = h
                        self.hash_vals.add(h)
        if os.path.exists(self.unvisited_file):
            with open(self.unvisited_file, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and url not in self.visited:
                        self.unvisited[url] = 1
        logger.info("State loaded from session directory.")

    def save_state(self):
        with open(self.unvisited_file, 'w') as f:
            for url in self.unvisited:
                f.write(url + "\n")
        with open(self.visited_file, 'w') as f:
            for url, h in self.visited.items():
                f.write(f"{h}<:>{url}\n")
        logger.info("State saved to session directory.")

    def load_buffer(self):
        # Load NDJSON lines from the buffer file into session_results.
        if os.path.exists(self.buffer_file):
            with open(self.buffer_file, 'r') as bf:
                for line in bf:
                    line = line.strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            self.session_results.append(obj)
                        except Exception as e:
                            logger.error(f"Error parsing buffered line: {line} -> {e}")
            logger.info(f"Loaded {len(self.session_results)} buffered entries.")

    def append_to_buffer(self, result):
        # Append a JSON object as a single line to the buffer file.
        try:
            with open(self.buffer_file, 'a') as bf:
                bf.write(json.dumps(result) + "\n")
        except Exception as e:
            logger.error(f"Error appending to buffer file: {e}")

    def get_host(self, url):
        parsed = urlparse(url)
        return parsed.netloc

    def clean_url(self, url):
        parsed = urlparse(url)
        path = re.sub(r'/+', '/', parsed.path)
        cleaned = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
        return cleaned.strip()

    def is_visited(self, url):
        return url in self.visited

    def download_file(self, url):
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                ext = os.path.splitext(urlparse(url).path)[1].lower()
                category = None
                for cat, exts in FILE_CATEGORIES.items():
                    if ext in exts:
                        category = cat
                        break
                if not category:
                    category = "doc"
                if not self.all_files:
                    if category == "doc" and not self.download_docs:
                        return
                    if category == "image" and not self.download_images:
                        return
                    if category == "audio" and not self.download_audio:
                        return
                    if category == "video" and not self.download_video:
                        return
                dest_dir = self.download_dirs.get(category)
                file_name = os.path.basename(urlparse(url).path)
                file_path = os.path.join(dest_dir, file_name)
                with open(file_path, 'wb') as out_file:
                    out_file.write(response.content)
                logger.info(f"Downloaded {category} file: {file_path} ({len(response.content)} bytes)")
            else:
                logger.error(f"Failed to download file from {url}: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {e}")

    def crawl(self, url):
        url = self.clean_url(url)
        if self.is_visited(url):
            logger.debug(f"Duplicate URL, skipping: {url}")
            self.unvisited.pop(url, None)
            return None

        host = self.get_host(url)
        logger.info(f"Crawling: {url} (unvisited: {len(self.unvisited)})")
        try:
            socket.gethostbyname(host)
        except socket.error:
            logger.warning(f"Cannot resolve host for {url}; marking as visited.")
            self.visited[url] = str(random.getrandbits(256))
            return None

        try:
            resp = self.session.get(url, timeout=5, allow_redirects=True)
            status_code = resp.status_code
            page_html = resp.text
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            self.visited[url] = str(random.getrandbits(256))
            return None

        if self.dynamic and self.driver:
            try:
                self.driver.get(url)
                time.sleep(2)
                page_html = self.driver.page_source
            except Exception as e:
                logger.error(f"Selenium dynamic fetch failed for {url}: {e}")

        if resp.history:
            for r in resp.history:
                self.visited[r.url] = str(random.getrandbits(256))
                logger.info(f"Redirect: {r.status_code} {r.url}")
            url = resp.url
            if not self.follow and self.get_host(url) != self.seed_host:
                logger.info("Redirected URL is outside the seed domain; skipping.")
                return None

        soup = BeautifulSoup(page_html, 'html.parser')
        base_url = url
        base_tag = soup.find('base')
        if base_tag and base_tag.get('href'):
            base_url = self.clean_url(base_tag['href'])

        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if text_hash in self.hash_vals:
            logger.info(f"Duplicate content hash {text_hash} for {url}; skipping.")
            self.visited[url] = text_hash
            self.unvisited.pop(url, None)
            return None
        self.hash_vals.add(text_hash)

        title = (soup.title.string.strip() if soup.title and soup.title.string else "undefined")
        result = {
            "url": url,
            "status_code": status_code,
            "sha256": text_hash,
            "content-type": resp.headers.get('content-type', ''),
            "title": title,
            "text": text,
            "links": []
        }

        for tag in soup.find_all('a', href=True):
            link = tag['href']
            if not re.match(r'^https?://', link):
                link = urljoin(base_url, link)
            link = self.clean_url(link)
            if link in ["/", ""]:
                continue
            ext = os.path.splitext(urlparse(link).path)[1].lower()
            if ext:
                if self.all_files:
                    self.download_file(link)
                    continue
                else:
                    downloaded = False
                    for cat, exts in FILE_CATEGORIES.items():
                        if ext in exts:
                            if (cat == "doc" and self.download_docs) or \
                               (cat == "image" and self.download_images) or \
                               (cat == "audio" and self.download_audio) or \
                               (cat == "video" and self.download_video):
                                self.download_file(link)
                                downloaded = True
                            break
                    if downloaded:
                        continue
            if link not in self.visited and link not in self.unvisited:
                if not self.follow:
                    if self.get_host(link) == self.seed_host:
                        self.unvisited[link] = 1
                else:
                    self.unvisited[link] = 1
            result["links"].append(link)

        if self.download_images or self.all_files:
            for img in soup.find_all("img", src=True):
                img_url = img['src']
                if not re.match(r'^https?://', img_url):
                    img_url = urljoin(url, img_url)
                self.download_file(img_url)

        self.visited[url] = text_hash
        self.unvisited.pop(url, None)
        if self.verbose >= 2:
            print(json.dumps(result, indent=4))
        if self.es:
            try:
                self.es.index(index="creeper", id=url, document=result)
            except Exception as e:
                logger.error(f"Elasticsearch indexing failed for {url}: {e}")
        self.session_results.append(result)
        self.append_to_buffer(result)
        return result

    def crawl_loop(self):
        while self.unvisited and not self.shutdown_flag:
            current_links = list(self.unvisited.keys())
            for link in current_links:
                if self.shutdown_flag:
                    break
                self.crawl(link)
                sys.stdout.flush()
        if self.shutdown_flag:
            self.save_state()
            sys.exit(1)

    def start(self):
        self.load_state()
        if self.seed not in self.visited:
            self.unvisited[self.seed] = 1
        self.crawl(self.seed)
        self.crawl_loop()
        self.save_state()
        if os.path.exists(self.unvisited_file):
            os.remove(self.unvisited_file)
        if self.driver:
            self.driver.quit()
        # Convert the buffer file (NDJSON) into a JSON array.
        session_path = os.path.join(self.output_dir, SESSION_JSON)
        buffer_data = []
        if os.path.exists(self.buffer_file):
            with open(self.buffer_file, 'r') as bf:
                for line in bf:
                    if line.strip():
                        buffer_data.append(json.loads(line.strip()))
        with open(session_path, "w") as f:
            json.dump(buffer_data, f, indent=4)
        logger.info(f"Session data written to {session_path}")

def main():
    parser = argparse.ArgumentParser(description="Optimized self-hosted web crawler with generic file downloads, session-based output, and resumable sessions. To resume an unfinished session, supply the session directory as the only argument.")
    parser.add_argument('session_dir', nargs='?', help="(Optional) Session directory to resume.")
    parser.add_argument('-u', '--url', help="Seed URL to start crawling from.")
    parser.add_argument('-f', '--follow', action='store_true', help="Follow links outside the seed domain.")
    parser.add_argument('-p', '--preserve', action='store_true', help="Preserve URI path (crawl entire domain).")
    parser.add_argument('-g', '--docs', action='store_true', help="Download document files (e.g., PDF, TXT, DOC).")
    parser.add_argument('-i', '--images', action='store_true', help="Download image files.")
    parser.add_argument('-a', '--audio', action='store_true', help="Download audio files.")
    parser.add_argument('-V', '--video', action='store_true', help="Download video files.")
    parser.add_argument('-A', '--all-files', action='store_true', help="Download all files regardless of type.")
    parser.add_argument('-x', '--dynamic', action='store_true', help="Enable dynamic page processing using Selenium.")
    parser.add_argument('-e', '--elasticsearch', help="Elasticsearch host (e.g., http://localhost:9200)")
    parser.add_argument('-c', '--clear', action='store_true', help="Clear session state (visited/unvisited files) and start fresh.")
    parser.add_argument('-D', '--directory', help="Specify output directory for downloads and session data. If not provided and not resuming, one is auto-created.")
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Increase verbosity level. -v prints logs; -vv prints logs and JSON entries.")

    args = parser.parse_args()

    # Determine if we are resuming an existing session.
    if args.session_dir and os.path.isdir(args.session_dir) and os.path.exists(os.path.join(args.session_dir, CONFIG_FILENAME)):
        output_dir = os.path.abspath(args.session_dir)
        with open(os.path.join(output_dir, CONFIG_FILENAME), "r") as f:
            config = json.load(f)
        if args.verbose:
            config["verbose"] = args.verbose
        logger.info(f"Resuming session from {output_dir}")
    else:
        if not args.url:
            parser.error("When not resuming a session, you must supply a seed URL with -u.")
        if args.directory:
            output_dir = os.path.abspath(args.directory)
        else:
            timestamp = int(time.time())
            output_dir = f"session_{urlparse(args.url).netloc}_{timestamp}"
        config = {
            "seed": args.url,
            "follow": args.follow,
            "preserve_path": args.preserve,
            "download_docs": args.docs,
            "download_images": args.images,
            "download_audio": args.audio,
            "download_video": args.video,
            "all_files": args.all_files,
            "dynamic": args.dynamic,
            "es_host": args.elasticsearch,
            "verbose": args.verbose,
            "output_dir": output_dir
        }
    if args.clear:
        for fname in [VISITED_FILENAME, UNVISITED_FILENAME]:
            path = os.path.join(config["output_dir"], fname)
            if os.path.exists(path):
                os.remove(path)
    if not os.path.exists(config["output_dir"]):
        os.makedirs(config["output_dir"])
    with open(os.path.join(config["output_dir"], CONFIG_FILENAME), "w") as f:
        json.dump(config, f, indent=4)
    logger.info(f"Session config saved to {os.path.join(config['output_dir'], CONFIG_FILENAME)}")

    crawler = WebCrawler(config)
    crawler.start()

if __name__ == "__main__":
    main()

