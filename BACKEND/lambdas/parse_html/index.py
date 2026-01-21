import json
import re
from html.parser import HTMLParser
#from bs4 import BeautifulSoup
import os
import sys
import urllib.request
from markdownify import markdownify as md

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared import openai_client  # noqa: E402
from shared import storage  # noqa: E402


def fetch_html(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


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
    html = re.sub(r"<header\b[^>]*>[\s\S]*?</header>", "", html, flags=re.IGNORECASE)
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
    return cleaned_content[:200000]


def handle_payload(payload, source: str):
    print("parse_html payload", {"source": source, "payload": payload})
    body = payload
    restaurant_url = body.get("restaurant_url")
    restaurant_id = body.get("restaurant_id")
    city = body.get("city", "")
    area = body.get("area", "")

    if not restaurant_url or not restaurant_id:
        raise ValueError("restaurant_url and restaurant_id are required")

    html = fetch_html(restaurant_url)
    html = md(html)
    #html = extract_relevant_content(html)
    #html = sanitize_html(html)
    print("parse_html fetched html", {"restaurant_id": restaurant_id, "html": html})
    csv_content = openai_client.parse_html_to_csv(
        html,
        {
            "restaurant_id": restaurant_id,
            "restaurant_url": restaurant_url,
            "city": city,
            "area": area,
        },
    )

    storage.save_weekly_csv(csv_content, restaurant_id, city=city, area=area)


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
