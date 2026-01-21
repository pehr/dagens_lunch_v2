import os
import sys
import urllib.parse

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared import openai_client  # noqa: E402
from shared import storage  # noqa: E402


def extract_restaurant_id(key: str):
    parts = key.split("/")
    if len(parts) >= 2 and parts[0] == "menus":
        return parts[1]
    return None


def handler(event, _context):
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
        csv_content = openai_client.parse_image_to_csv(binary, {"restaurant_id": restaurant_id})
        storage.save_weekly_csv(csv_content, restaurant_id)

    return {"ok": True}
