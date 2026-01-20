import os
import sys
import urllib.parse

import boto3

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared import date_utils  # noqa: E402
from shared import openai_client  # noqa: E402

s3 = boto3.client("s3")


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

        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj.get("Body")
        if not body:
            raise ValueError("Menu object body was empty")

        binary = body.read()
        csv_content = openai_client.parse_image_to_csv(binary, {"restaurant_id": restaurant_id})
        weekly_key = date_utils.build_weekly_key(restaurant_id)

        s3.put_object(
            Bucket=os.environ["WEEKLY_LUNCHMENUS_BUCKET"],
            Key=weekly_key,
            Body=csv_content.encode("utf-8"),
            ContentType="text/csv",
            Metadata={"restaurant_id": restaurant_id},
        )

    return {"ok": True}
