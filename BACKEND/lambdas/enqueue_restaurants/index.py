import json
import os

import boto3


ddb = boto3.client("dynamodb")
sqs = boto3.client("sqs")


def handler(_event, _context):
    table_name = os.environ["TABLE_NAME"]
    queue_url = os.environ["QUEUE_URL"]
    last_key = None
    total = 0

    while True:
        scan_args = {
            "TableName": table_name,
            "FilterExpression": "#sk = :info",
            "ExpressionAttributeNames": {"#sk": "sk"},
            "ExpressionAttributeValues": {":info": {"S": "INFO"}},
        }
        if last_key:
            scan_args["ExclusiveStartKey"] = last_key

        result = ddb.scan(**scan_args)
        for item in result.get("Items", []):
            url = item.get("url", {}).get("S")
            restaurant_id = item.get("restaurant_id", {}).get("S")
            if not url or not restaurant_id:
                continue

            message = {
                "restaurant_url": url,
                "restaurant_id": restaurant_id,
                "city": item.get("city", {}).get("S", ""),
                "area": item.get("area", {}).get("S", ""),
            }

            sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
            total += 1

        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break

    return {"ok": True, "total": total}
