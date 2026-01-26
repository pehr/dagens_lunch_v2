import argparse
import json
import os
from pathlib import Path

import boto3


def load_restaurants(sources_dir: Path):
    restaurants = []
    for path in sorted(sources_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        restaurant_id = path.stem
        payload["restaurant_id"] = restaurant_id
        payload["sk"] = "INFO"
        restaurants.append(payload)
    return restaurants


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="DynamoDB table name")
    parser.add_argument(
        "--sources-dir",
        default="RestaurantSources",
        help="Path to Restaurant Sources directory",
    )
    args = parser.parse_args()

    sources_dir = (Path(__file__).resolve().parents[1] / args.sources_dir).resolve()
    if not sources_dir.exists():
        raise SystemExit(f"Sources dir not found: {sources_dir}")

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(args.table)

    restaurants = load_restaurants(sources_dir)
    with table.batch_writer() as batch:
        for item in restaurants:
            batch.put_item(Item=item)
    print(f"Imported {len(restaurants)} restaurants into {args.table}")


if __name__ == "__main__":
    main()
