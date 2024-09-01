import logging
import requests
from bs4 import BeautifulSoup
import json
import re
import time
from threading import Thread
from flask import Flask, Response, stream_with_context, request
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    filename='rss_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

log_lines = []

def load_keywords(keywords_url):
    try:
        response = requests.get(keywords_url)
        response.raise_for_status()
        keywords_data = response.json()
        keywords = [keyword.lower() for k in keywords_data.values() for keyword in k]
        logging.info('Keywords loaded successfully.')
        return keywords
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to load keywords from {keywords_url}: {str(e)}")
        return []

def scrape_recursive(url, base_url, keywords, visited_urls):
    if url in visited_urls:
        return
    visited_urls.add(url)

    try:
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()
        final_url = response.url
        log_message = f"Scraping URL: {final_url}"
        logging.info(log_message)
        log_lines.append(log_message)

        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text().lower()

        title = soup.title.string if soup.title else "No title"
        content = ' '.join(p.get_text() for p in soup.find_all('p'))

        for keyword in keywords:
            if keyword in page_text:
                match_message = f"Match found for keyword '{keyword}'\nTitle: {title}\nContent: {content[:300]}...\nURL: {final_url}"
                logging.info(match_message)
                log_lines.append(match_message)
                break

        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/'):
                href = urljoin(base_url, href)
            if href.startswith(base_url):
                scrape_recursive(href, base_url, keywords, visited_urls)

    except requests.exceptions.RequestException as e:
        error_message = f"Failed to scrape {url}: {str(e)}"
        logging.error(error_message)
        log_lines.append(error_message)

def periodic_scraping(base_url, keywords_url, interval):
    keywords = load_keywords(keywords_url)
    while True:
        visited_urls = set()
        scrape_recursive(base_url, base_url, keywords, visited_urls)
        time.sleep(interval)

@app.route('/stream')
def stream():
    def generate():
        while True:
            if log_lines:
                line = log_lines.pop(0)
                yield f"data: {line}\n\n"
            time.sleep(1)

    return Response(stream_with_context(generate()), content_type='text/event-stream')

if __name__ == "__main__":
    base_url = "https://www.cbc.ca/news"
    keywords_url = "https://raw.githubusercontent.com/berlintay/reactionary/main/irc/rss/keywords.json"
    scrape_interval = 600  # Scrape every 10 minutes

    # Start the periodic scraper in a background thread
    scraper_thread = Thread(target=periodic_scraping, args=(base_url, keywords_url, scrape_interval))
    scraper_thread.daemon = True
    scraper_thread.start()

    # Start the Flask server
    app.run(host='0.0.0.0', port=5000)
