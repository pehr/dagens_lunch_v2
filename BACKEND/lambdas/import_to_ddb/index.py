import csv
import io
import os
import sys
import urllib.parse

import boto3

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared import date_utils  # noqa: E402

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")


def normalize_price(raw: str):
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else None


def parse_csv(content: str):
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        day = (row.get("day") or "").strip().lower()
        lunch = (row.get("lunch") or "").strip()
        price = (row.get("price") or "").strip()
        tags = (row.get("tags") or "").strip()
        if day not in {"mon", "tue", "wed", "thu", "fri"} or not lunch:
            continue
        rows.append({
            "day": day,
            "name": lunch,
            "price": price,
            "tags": tags,
        })
    return rows


def get_restaurant_info(table, restaurant_id: str):
    result = table.get_item(Key={"restaurant_id": restaurant_id, "sk": "INFO"})
    return result.get("Item")


def handler(event, _context):
    table = ddb.Table(os.environ["TABLE_NAME"])

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        weekly_info = date_utils.parse_weekly_key(key)

        if not weekly_info:
            continue

        restaurant_id = weekly_info["restaurant_id"]
        week = f"{weekly_info['year']}_{weekly_info['week']}"

        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj.get("Body")
        content = body.read().decode("utf-8") if body else ""
        metadata = obj.get("Metadata") or {}

        rows = parse_csv(content)
        if not rows:
            continue

        info = get_restaurant_info(table, restaurant_id) or {}
        city = metadata.get("city") or info.get("city")
        area = metadata.get("area") or info.get("area")

        grouped = {}
        for row in rows:
            dish = {
                "name": row["name"],
                "tags": [tag for tag in (t.strip() for t in row["tags"].split("|")) if tag],
            }
            price_value = normalize_price(row["price"])
            if price_value is not None:
                dish["price"] = price_value
            grouped.setdefault(row["day"], []).append({
                **dish
            })

        for day, dishes in grouped.items():
            item = {
                "restaurant_id": restaurant_id,
                "sk": f"MENU#{week}#{day}",
                "week": week,
                "day": day,
                "dishes": dishes,
            }
            if city:
                item["city"] = city
            if area:
                item["area"] = area
            table.put_item(Item=item)

    return {"ok": True}
