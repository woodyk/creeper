#!/usr/bin/env python3
#
# mycrawler.py -- Wadih Khairallah
#
# Great sites for testing:
#   https://crawler-test.com/
#   https://books.toscrape.com
#
# Ubuntu Server Setup
# wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
# sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
# sudo apt-get update
# sudo apt-get install google-chrome-stable
# sudo apt-get install firefox

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
#from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse, urlunparse, urljoin
import json
import hashlib
import sys
import random
import requests
import socket
import html
from os.path import exists
import os
import getopt
import signal
import re
import time
from elasticsearch import Elasticsearch
import shutil

# Get options
argv = sys.argv[1:]

# Global variables
visitedFile = '/tmp/visited.txt'
unvisitedFile = '/tmp/unvisited.txt'
follow = False;
download_pictures = True  # Added option for downloading pictures
preservePath = False
download_pdf = False
depth = 5
visited = {}
unvisited = {}
hashVals = [] 
Sentry = False
es = False
dynamic = False

# Set the user agent for requests
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'}

# Help output
def help():
    print(__file__, " -u [seed url] [options]")
    print("\t-u\tSeed URL to start with.")
    print("\t-h\tThis help output.")
    print("\t-e\tElastic search host.")
    print("\t-p\tPreserve URI path.")
    print("\t-g\tDownload PDF files.")
    print("\t-d\tEnable dynamic page processing.")
    print("\t-f\tMake creeper follow outside links.")
    print("\t-c\tClear out visited and unvisited domains lists.")
    sys.exit()

# Signal Handler
def handler(signum, frame):
    global Sentry
    Sentry = True 

# pdf download function
def download_pdf_file(url):
    response = requests.get(url, stream=True)
    file_name = url.split("/")[-1]
    with open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

# picture download function
def download_picture(url):
    response = requests.get(url, stream=True)
    file_name = url.split("/")[-1]
    if not any(file_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
        return
    with open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

# Capture signals
signal.signal(signal.SIGINT, handler)

# Populate our visited and unvisited link files.
def writeLinks():
    # populate unvisited
    f = open(unvisitedFile, "w")
    for link in unvisited:
        f.write(link + "\n")
   
    f.close()

    #populate visited
    f = open(visitedFile, "w")
    for link in visited:
        f.write(visited[link] + "<:>" + link + "\n")
    
    f.close()

# Printing to stderr
def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

def checkVisited(url):
    if url in visited:
        eprint("\tDuplicate URL: skipping...")
        try:
           del unvisited[url]
        except:
            pass

def urlClean(url):
    orig = url
    san = urlparse(url)

    path = re.sub(r'\/+', '/', san.path)

    url = urljoin(url, path)

    if san.query:
        url += '?' + san.query
    
    return url

def urlHost(url):
    san = urlparse(url)

    return san.netloc

# Extract data from given URLs
def crawl(url):
    retVals = {}
    textHash = str()
    status_code = int()

    hostname = urlHost(url) 

    retVals["url"] = url 

    eprint("Links:" + '[' + str(len(unvisited)) + '] ' + url)

    if checkVisited(url) == 1:
        return

    try:
        socket.gethostbyname(hostname)
    except:
        visited[url] = str(random.getrandbits(256))
        return

    try:
        x = requests.get(url, timeout=5, allow_redirects=True, headers=headers)
        status_code = x.status_code 
        html = x.text
    except:
        visited[url] = str(random.getrandbits(256))
        return

    if dynamic:
        driver.get(url)
        time.sleep(2)
        html = driver.page_source
        #perfLog = driver.get_log('performance')

    if x.history:
        retVals['redirect'] = {}
        getCode = True 
        for i in x.history:

            if getCode:
                status_code = i.status_code
                getCode = False

            retVals['redirect'][i.url] = i.status_code
            visited[i.url] = str(random.getrandbits(256))
            eprint("\tredir: " + str(i.status_code) + " " + i.url)

        retVals['redirect'][x.url] = x.status_code
        eprint("\tredir: " + str(x.status_code) + " " + x.url)
        url = x.url

        redirHost = urlHost(x.url)

        if not follow:
            if not re.search(r"^.*://.*" + seedHost, url):
                return
         
        if checkVisited(url) == 1:
            return

    if status_code:
        soup = BeautifulSoup(html, 'html.parser')

        # Check for base url
        base = soup.find('base')
        if base:
            try:
                del unvisited[url]
            except:
                pass

            visited[url] = str(random.getrandbits(256))
            url = base['href']
            url = urlClean(url)

        # Get rendered text
        text = re.sub(r'\n+', '\n', soup.get_text())
        text = re.sub(r'\s+', " ", text)
        text = re.sub(r'^ | $', "", text) 

        # Get Title
        try:
            title = soup.title.string
        except:
            title = "undefined"

        if title:
            title = re.sub(r'\n+', '\n', title)
            title = re.sub(r'\s+', " ", title)
            title = re.sub(r'^ | $', "", title) 

        # Create sha256 hash for page contents
        hashObj = hashlib.sha256(text.encode())
        textHash = hashObj.hexdigest()

        if textHash in hashVals:
            eprint("\tHex match: " + textHash + " skipping...")
            visited[url] = textHash 
            try:
                del unvisited[url]
            except:
                pass

            return
        else:
            hashVals.append(textHash)

        retVals["status_code"] = status_code
        retVals['sha256'] = textHash
        retVals["content-type"] = x.headers['content-type']
        retVals["title"] = title 
        retVals["text"] = text
        retVals["links"] = [];

        for atag in soup.find_all(["a"]):
            link = atag.get('href')

            if link and link.endswith('.pdf') and download_pdf:
                download_pdf_file(link)

            if link:
                if link == "/":
                    continue

                if not re.search(r'^.*:\/\/', link):
                    link = urljoin(url, link)

                link = urlClean(link)
                
                if link not in retVals["links"]:
                    if preservePath:
                        if re.search(f"^{seed}.*", link):
                            unvisited[link] = 1;

                    elif not follow:
                        if re.search(r"^.*://.*" + seedHost, link):
                                unvisited[link] = 1;
                    else:
                        unvisited[link] = 1;

                    retVals["links"].append(link)
                    

    try:
        del unvisited[url]
    except:
        pass

    visited[url] = textHash 
    print(json.dumps(retVals, indent=4))

    if es:
        eresp = es.index(index="creeper", id=url, document=retVals)

    # Download pictures
    if download_pictures:
        for imgtag in soup.find_all("img"):
            img_url = imgtag.get("src")
            if img_url:
                if not re.search(r'^.*:\/\/', img_url):
                    img_url = urljoin(url, img_url)
                download_picture(img_url)

    return retVals

# Loop throught links list
def loop(links):
    for link in links.copy():
        #time.sleep(1)
        crawl(link)
        sys.stdout.flush()

        # Handle our exit sentry
        if Sentry:
            writeLinks()
            sys.exit(1)

def start(seed):
    # Populate visited dict if file exists.
    if exists(visitedFile):
        f = open(visitedFile, "r")
        lines = f.readlines()
    
        for line in lines:
            line = line.strip()
            values = line.split('<:>')
            visited[values[1]] = values[0]
            hashVals.append(values[0])
    
        f.close()

    # Populate unvisited dict if file exists.
    if exists(unvisitedFile):
        f = open(unvisitedFile, "r")
        lines = f.readlines()
    
        for line in lines:
            line = line.strip()
            if line not in visited:
                unvisited[line] = 1

        f.close()

    # Begin crawling with the seed url.
    crawl(seed)

    # While we have unvisited links loop.
    while len(unvisited) > 0:
        loop(unvisited)

    # On finish write visited data and delete unvisited. 
    writeLinks()
    os.remove(unvisitedFile)

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(argv, "e:u:h:dfpcg")
    except:
        help()

    if not opts:
        help()

    # Populate arguments
    for opt, arg in opts:
        if opt == '-u':
            seed = arg
            seedHost = urlHost(seed) 
        elif opt == '-f':
            follow = True 
        elif opt == '-c':
            if exists(visitedFile):
                os.remove(visitedFile)
            if exists(unvisitedFile):
                os.remove(unvisitedFile)
        elif opt == '-d':
            dynamic = True

            # Firefox
            options = webdriver.FirefoxOptions()
            options.headless = True
            driver = webdriver.Firefox(service=webdriver.firefox.service.Service(GeckoDriverManager().install(), log_path='/dev/null'), options=options)

            # Google Chrome
            #options = webdriver.ChromeOptions()
            #options.headless = True
            #desired_capabilities = DesiredCapabilities.CHROME
            #desired_capabilities['goog:loggingPrefs'] = {'performance':'ALL'}
            #driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=options, desired_capabilities=desired_capabilities)
            #driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=options)

        elif opt == '-p':
            preservePath = True
        elif opt == '-e':
            if re.search(r'^http.*:\/\/.*:\d{1,5}', arg):
                es = Elasticsearch(arg)
            else:
                help()
        elif opt == '-g':
            download_pdf = True
        elif opt == '-h':
            help()
        elif opt == '-l':
            level = arg
        elif opt == '-i':
            download_pictures = True

    start(seed)
