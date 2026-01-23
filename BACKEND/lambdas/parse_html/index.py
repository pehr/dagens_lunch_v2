import json
import re
from html.parser import HTMLParser
#from bs4 import BeautifulSoup
import os
import sys
import time
import requests
from markdownify import markdownify as md

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared import openai_client  # noqa: E402
from shared import storage  # noqa: E402


def fetch_html(url: str) -> str:
    print("Fetch HTML", {"url": url})
    timeout_seconds = int(os.environ.get("FETCH_TIMEOUT_SECONDS", "10"))
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
    }
    start = time.monotonic()
    try:
        print("fetch_html request start", {"url": url})
        response = requests.get(url, headers=headers, timeout=(timeout_seconds, timeout_seconds))
        print("fetch_html response received", {"url": url, "status": response.status_code})
        response.raise_for_status()
        print("fetch_html response ok", {"url": url, "length": len(response.text)})
        return response.text
    except Exception as exc:
        elapsed = round(time.monotonic() - start, 2)
        print("fetch_html failed", {"url": url, "seconds": elapsed, "error": str(exc)})
        raise


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []
        self._skip_depth = 0

    def handle_starttag(self, tag, _attrs):
        if tag in {
            "head",
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "noscript",
            "svg",
        }:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {
            "head",
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "noscript",
            "svg",
        }:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._skip_depth == 0 and data:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join(self._chunks)


# def extract_relevant_content(html_content):
#     soup = BeautifulSoup(html_content, 'html.parser')
    
#     # Remove all script and style elements
#     for script in soup(["script", "style"]):
#         script.decompose()
    
#     # Adjust these selectors based on the structure of the webpage you're parsing
#     # This is just an example - you'll need to inspect the HTML and choose appropriate selectors
#     menu_content = soup.find('div', class_='menu-content')
#     if menu_content:
#         extracted_content = str(menu_content)
#     else:
#         # If we can't find a specific element, use the entire body content
#         body = soup.find('body')
#         extracted_content = body.get_text() if body else soup.get_text()
    
#     # Remove extra whitespace and limit the content length
#     cleaned_content = ' '.join(extracted_content.split())
#     return cleaned_content[:100000]  # Adjust this number as needed, keeping it under 150,000



def sanitize_html(html: str) -> str:
    html = re.sub(r"<head\b[^>]*>[\s\S]*?</head>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<nav\b[^>]*>[\s\S]*?</nav>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<footer\b[^>]*>[\s\S]*?</footer>", "", html, flags=re.IGNORECASE)
    #html = re.sub(r"<header\b[^>]*>[\s\S]*?</header>", "", html, flags=re.IGNORECASE) #Removed for problems w Olearys
    html = re.sub(r"<aside\b[^>]*>[\s\S]*?</aside>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<noscript\b[^>]*>[\s\S]*?</noscript>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<svg\b[^>]*>[\s\S]*?</svg>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<img\b[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(
        r"<[^>]+\btype\s*=\s*(['\"])application/json\1[^>]*>[\s\S]*?</[^>]+>",
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r"\sdata-[\w:-]+\s*=\s*(['\"]).{200,}?\1",
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(r"\sstyle\s*=\s*(['\"]).*?\1", "", html, flags=re.IGNORECASE)
    extractor = _TextExtractor()
    extractor.feed(html)
    cleaned_content = " ".join(extractor.text().split())
    return cleaned_content
    #return cleaned_content[:200000]


def handle_payload(payload, source: str):
    print("parse_html payload", {"source": source, "payload": payload})
    body = payload
    restaurant_url = body.get("restaurant_url")
    restaurant_id = body.get("restaurant_id")
    city = body.get("city", "")
    area = body.get("area", "")

    if not restaurant_url or not restaurant_id:
        raise ValueError("restaurant_url and restaurant_id are required")

    print("parse_html fetch start", {"restaurant_id": restaurant_id, "url": restaurant_url})
    html = fetch_html(restaurant_url)
    print("parse_html fetch done", {"restaurant_id": restaurant_id, "html_len": len(html)})
    html = sanitize_html(html)
    print("parse_html markdownify start", {"restaurant_id": restaurant_id})
    html = md(html)
    print("parse_html markdownify done", {"restaurant_id": restaurant_id, "md_len": len(html)})
    #html = extract_relevant_content(html)
    #html = sanitize_html(html)
    print("parse_html openai start", {"restaurant_id": restaurant_id})
    csv_content = openai_client.parse_html_to_csv(
        html,
        {
            "restaurant_id": restaurant_id,
            "restaurant_url": restaurant_url,
            "city": city,
            "area": area,
        },
    )

    print("parse_html save to s3", {"restaurant_id": restaurant_id})
    storage.save_weekly_csv(csv_content, restaurant_id, city=city, area=area)
    print(
        "parse_html done",
        {
            "restaurant_id": restaurant_id,
            "city": city,
            "area": area,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )


def handler(event, _context):
    print("parse_html event", {"event": event})
    records = event.get("Records")
    if records:
        for record in records:
            print("parse_html record", {"record": record})
            body = json.loads(record.get("body", "{}"))
            handle_payload(body, "sqs")
        return {"ok": True}

    if isinstance(event, dict):
        handle_payload(event, "direct")
        return {"ok": True}

    raise ValueError("Unsupported event format")
