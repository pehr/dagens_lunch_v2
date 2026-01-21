import os

import boto3

from shared import date_utils

s3 = boto3.client("s3")


def get_s3_object(bucket: str, key: str):
    return s3.get_object(Bucket=bucket, Key=key)


def save_weekly_csv(csv_text: str, restaurant_id: str, city: str = "", area: str = ""):
    key = date_utils.build_weekly_key(restaurant_id)
    metadata = {"restaurant_id": restaurant_id}
    if city:
        metadata["city"] = city
    if area:
        metadata["area"] = area

    s3.put_object(
        Bucket=os.environ["WEEKLY_LUNCHMENUS_BUCKET"],
        Key=key,
        Body=csv_text.encode("utf-8"),
        ContentType="text/csv",
        Metadata=metadata,
    )
