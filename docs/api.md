# API

Base URL: API Gateway URL output by the stack.

All responses are JSON and include `Access-Control-Allow-Origin: *`.

## GET /restaurants

List all restaurants where `sk = "INFO"`.

Response 200:

```json
{
  "items": [
    {
      "restaurant_id": "goldendays",
      "sk": "INFO",
      "restaurant_name": "Golden Days",
      "url": "https://www.goldendays.se/",
      "city": "goteborg",
      "city_name": "Göteborg",
      "area": "innerstaden",
      "info": "TILL LUNCHEN INGÅR EN FRÄSCH SALLADSBUFFÉ, NYBRYGGT KAFFE OCH KAKA",
      "lunch_hours": "11.00-15.00",
      "address": "",
      "coordinates": "",
      "phone": ""
    }
  ]
}
```

## GET /restaurants/{restaurant_id}

Get a single restaurant info item by id.

Path params:
- `restaurant_id` (string)

Response 200:

```json
{
  "items": [
    {
      "restaurant_id": "goldendays",
      "sk": "INFO",
      "restaurant_name": "Golden Days",
      "url": "https://www.goldendays.se/",
      "city": "goteborg",
      "city_name": "Göteborg",
      "area": "innerstaden",
      "info": "TILL LUNCHEN INGÅR EN FRÄSCH SALLADSBUFFÉ, NYBRYGGT KAFFE OCH KAKA",
      "lunch_hours": "11.00-15.00",
      "address": "",
      "coordinates": "",
      "phone": ""
    }
  ]
}
```

## GET /restaurants/{restaurant_id}/{week}

Get menu items for a restaurant and week.

Path params:
- `restaurant_id` (string)
- `week` (string, format `YYYY_WW`, e.g. `2026_04`)

Response 200:

```json
{
  "items": [
    {
      "restaurant_id": "goldendays",
      "sk": "MENU#2026_04#fri",
      "city": "goteborg",
      "area": "innerstaden",
      "week": "2026_04",
      "day": "fri",
      "dishes": [
        {
          "name": "Kycklingsoppa",
          "price": 155,
          "tags": ["soppa", "kyckling", "svensk"]
        },
        {
          "name": "Fläskfilé med pepparsås och potatisgratäng",
          "price": 155,
          "tags": ["kött", "husmanskost", "svensk"]
        }
      ]
    }
  ]
}
```

## GET /lunch/{city}/{week}/{day}

List menu items for a city on a specific week/day. Uses the `by_location_and_day`
GSI. Optional `area` filter is applied as a non-key filter.

Path params:
- `city` (string, lowercase)
- `week` (string, format `YYYY_WW`, e.g. `2026_04`)
- `day` (string, `mon|tue|wed|thu|fri`)

Query params:
- `area` (string, optional)

Response 200:

```json
{
  "items": [
    {
      "restaurant_id": "goldendays",
      "sk": "MENU#2026_04#fri",
      "city": "goteborg",
      "area": "innerstaden",
      "week": "2026_04",
      "day": "fri",
      "dishes": [
        {
          "name": "Laxfilé med dillsås och pressad potatis",
          "price": 155,
          "tags": ["fisk", "husmanskost", "svensk"]
        }
      ]
    }
  ]
}
```
