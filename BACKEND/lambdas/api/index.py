import json
import os

import boto3


ddb = boto3.resource("dynamodb")


def response(status_code: int, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def list_restaurants(table):
    result = table.scan(
        FilterExpression="#sk = :info",
        ExpressionAttributeNames={"#sk": "sk"},
        ExpressionAttributeValues={":info": "INFO"},
    )
    return result.get("Items", [])


def get_restaurant_info(table, restaurant_id: str):
    result = table.get_item(Key={"restaurant_id": restaurant_id, "sk": "INFO"})
    item = result.get("Item")
    return [item] if item else []


def get_restaurant_week(table, restaurant_id: str, week: str):
    result = table.query(
        KeyConditionExpression="restaurant_id = :id AND begins_with(#sk, :prefix)",
        ExpressionAttributeNames={"#sk": "sk"},
        ExpressionAttributeValues={":id": restaurant_id, ":prefix": f"MENU#{week}"},
    )
    return result.get("Items", [])


def get_lunch_by_location(table, gsi_name: str, city: str, area: str | None, week: str, day: str):
    if area:
        result = table.query(
            IndexName=gsi_name,
            KeyConditionExpression="#city = :city AND #area = :area AND #week = :week AND #day = :day",
            ExpressionAttributeNames={
                "#city": "city",
                "#area": "area",
                "#week": "week",
                "#day": "day",
            },
            ExpressionAttributeValues={
                ":city": city,
                ":area": area,
                ":week": week,
                ":day": day,
            },
        )
        return result.get("Items", [])

    result = table.scan(
        FilterExpression="#city = :city AND #week = :week AND #day = :day",
        ExpressionAttributeNames={
            "#city": "city",
            "#week": "week",
            "#day": "day",
        },
        ExpressionAttributeValues={
            ":city": city,
            ":week": week,
            ":day": day,
        },
    )
    return result.get("Items", [])


def handler(event, _context):
    if event.get("httpMethod") != "GET":
        return response(405, {"message": "Method not allowed"})

    table = ddb.Table(os.environ["TABLE_NAME"])
    gsi_name = os.environ["GSI_NAME"]

    resource = event.get("resource")
    params = event.get("pathParameters") or {}

    if resource == "/restaurants":
        return response(200, {"items": list_restaurants(table)})

    if resource == "/restaurants/{restaurant_id}":
        restaurant_id = params.get("restaurant_id")
        if not restaurant_id:
            return response(400, {"message": "restaurant_id is required"})
        return response(200, {"items": get_restaurant_info(table, restaurant_id)})

    if resource == "/restaurants/{restaurant_id}/{week}":
        restaurant_id = params.get("restaurant_id")
        week = params.get("week")
        if not restaurant_id or not week:
            return response(400, {"message": "restaurant_id and week are required"})
        return response(200, {"items": get_restaurant_week(table, restaurant_id, week)})

    if resource == "/lunch/{city}/{week}/{day}":
        city = params.get("city")
        week = params.get("week")
        day = params.get("day")
        area = (event.get("queryStringParameters") or {}).get("area")

        if not city or not week or not day:
            return response(400, {"message": "city, week, and day are required"})

        items = get_lunch_by_location(table, gsi_name, city, area, week, day)
        return response(200, {"items": items})

    return response(404, {"message": "Not found"})
