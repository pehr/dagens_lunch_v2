import json
import os
import sys
import urllib.request

import boto3

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared import date_utils  # noqa: E402
from shared import openai_client  # noqa: E402

s3 = boto3.client("s3")


def fetch_html(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def handle_record(record):
    body = json.loads(record.get("body", "{}"))
    restaurant_url = body.get("restaurant_url")
    restaurant_id = body.get("restaurant_id")
    city = body.get("city", "")
    area = body.get("area", "")

    if not restaurant_url or not restaurant_id:
        raise ValueError("restaurant_url and restaurant_id are required")

    html = fetch_html(restaurant_url)
    csv_content = openai_client.parse_html_to_csv(
        html,
        {
            "restaurant_id": restaurant_id,
            "restaurant_url": restaurant_url,
            "city": city,
            "area": area,
        },
    )

    key = date_utils.build_weekly_key(restaurant_id)

    s3.put_object(
        Bucket=os.environ["WEEKLY_LUNCHMENUS_BUCKET"],
        Key=key,
        Body=csv_content.encode("utf-8"),
        ContentType="text/csv",
        Metadata={
            "restaurant_id": restaurant_id,
            "city": city,
            "area": area,
        },
    )


def handler(event, _context):
    for record in event.get("Records", []):
        handle_record(record)

    return {"ok": True}
