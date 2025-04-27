# Creeper: A Python Web Crawler

## Overview
`creeper.py` is an optimized self-hosted web crawler designed for efficient web scraping with the ability to download various file types, maintain session states, and handle dynamically generated content. This script supports resumable sessions, allowing users to pause and continue crawls seamlessly.

## Features
- **Session-Based Crawling**: Start new sessions or resume from previously interrupted ones.
- **File Downloads**: Supports downloading documents, images, audio, and video files.
- **Dynamic Content Crawling**: Handles pages rendered with JavaScript using Selenium.
- **Data Storage**: Saves session state (configuration, visited/unvisited URLs, logs) in designated directories.
- **Elasticsearch Integration**: Option to index crawled data into an Elasticsearch instance.
- **Verbose Logging**: Provides customizable logging for monitoring crawl activities.

## Prerequisites
Ensure that you have the following dependencies installed:
- Python 3.x
- Required Python packages:
    ```bash
    pip install requests beautifulsoup4 elasticsearch selenium webdriver-manager
    ```

## Usage

### Command-Line Arguments
The script can be run with various command-line arguments:

```bash
./creeper.py [session_directory] [options]
```

#### Options:
- `session_directory`: (Optional) Specify a directory to resume an existing session.
- `-u`, `--url <url>`: Seed URL to start crawling from.
- `-f`, `--follow`: Follow links outside the seed domain.
- `-p`, `--preserve`: Preserve URI path during crawling.
- `-g`, `--docs`: Download document files (PDF, TXT, DOC).
- `-i`, `--images`: Download image files.
- `-a`, `--audio`: Download audio files.
- `-V`, `--video`: Download video files.
- `-A`, `--all-files`: Download all file types.
- `-x`, `--dynamic`: Enable dynamic content processing using Selenium.
- `-e`, `--elasticsearch <host>`: Elasticsearch host URL (e.g., http://localhost:9200).
- `-c`, `--clear`: Clear session state and start fresh.
- `-D`, `--directory <path>`: Specify output directory for downloads and session data.
- `-v`, `--verbose`: Increase verbosity level.
    - `-v`: Print logs.
    - `-vv`: Print logs and JSON entries.

### Example Commands
1. **Start a new crawl session**:
   ```bash
   ./creeper.py -u https://crawler-test.com/ -g -i
   ```

2. **Resume a previous session**:
   ```bash
   ./creeper.py /path/to/session_directory
   ```

3. **Crawl dynamically generated content**:
   ```bash
   ./creeper.py -u https://example.com/ -x
   ```

## Directory Structure
The script creates a session directory containing:
- `config.json`: Configuration settings for the session.
- `visited.txt`: List of visited URLs.
- `unvisited.txt`: List of URLs yet to be crawled.
- `session.json`: Collected session data in JSON format.
- `session.log`: Log file for crawl events.
- `session_buffer.ndjson`: Temporary buffer for collected crawl data.

## Logging
Logging is performed to `session.log`, with verbosity determined by the `-v` options. Use `-vv` for more detailed output including JSON entries from crawled pages.

## Requirements for Dynamic Crawling
To enable dynamic crawling support via Selenium:
1. Ensure the required WebDriver is installed.
2. Use the `-x` option when running the script.

## Authors
Original author: **Wadih Khairallah**

## License
This project is licensed under the MIT License.

## Tips
- Utilize the provided test websites like `https://crawler-test.com/` and `https://books.toscrape.com` for testing.
- Monitor the log carefully for any errors or warnings that may occur during crawling.
- Ensure that website policies allow crawling before scraping their contents.

For further assistance, refer to the comments within the script or explore the documentation of the libraries used.
