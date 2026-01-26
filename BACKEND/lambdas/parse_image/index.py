import os
import sys
import urllib.parse
import time

import boto3

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared import openai_client  # noqa: E402
from shared import storage  # noqa: E402

ddb = boto3.resource("dynamodb")


def extract_restaurant_id(key: str):
    parts = key.split("/")
    if len(parts) >= 2 and parts[0] == "menus":
        return parts[1]
    return None


def handler(event, _context):
    table = ddb.Table(os.environ["TABLE_NAME"])
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        restaurant_id = extract_restaurant_id(key)

        if not restaurant_id:
            continue

        obj = storage.get_s3_object(bucket, key)
        body = obj.get("Body")
        if not body:
            raise ValueError("Menu object body was empty")

        binary = body.read()
        info = table.get_item(Key={"restaurant_id": restaurant_id, "sk": "INFO"}).get("Item", {})
        city = info.get("city", "")
        area = info.get("area", "")

        csv_content = openai_client.parse_image_to_csv(
            binary,
            {"restaurant_id": restaurant_id, "city": city, "area": area},
        )
        storage.save_weekly_csv(csv_content, restaurant_id, city=city, area=area)
        print(
            "parse_image done",
            {
                "restaurant_id": restaurant_id,
                "city": city,
                "area": area,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

    return {"ok": True}
