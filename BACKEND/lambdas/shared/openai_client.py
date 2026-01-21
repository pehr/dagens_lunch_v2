import base64
import csv
import io
import json
import os
import urllib.request

import boto3

DEFAULT_MODEL = "gpt-4.1-2025-04-14"
#DEFAULT_MODEL = "gpt-5-nano-2025-08-07" #"gpt-5-nano"
_OPENAI_SECRET_CACHE = {}
SYSTEM_PROMPT = (
    f"""You extract restaurant lunch menus and return a clean CSV.
Return only CSV text with a header row. Use UTF-8 and keep Swedish diacritics.
Format and rules:
- Header: day,lunch,price,tags
- One row per dish per day (duplicate dishes across days when relevant).
- day must be lowercase: mon,tue,wed,thu,fri (ignore weekends unless explicitly present).
- price is numeric; if missing, leave blank.
- tags are lowercase and separated by " | " (pipe with spaces). Use a few best-fit tags.
- Quote fields containing commas or quotes; escape quotes with double quotes.
- Output only CSV, no explanations or markdown.

Example:
day,lunch,price,tags
mon,"Pocherad torsk med kokt potatis, räkor, ägg, pepparrot & brynt smör.",169,fisk | svenskt | husmanskost
mon,"Marinerad kycklingstek med rostad potatis & rotfrukter",169,husmanskost
tue,"Gravad lax med dillstuvad potatis serveras med citron och sallad på rädisa & sockerärtor.",169,fisk | svenskt | husmanskost
"""
)
HTML_PROMPT = (
    f"""Parse the following HTML content and extract the lunch menu for each day of the week.
For each day, provide the day of the week, what's for lunch, and the price. There might be multiple lunch options for a day. Keep all text in Swedish.
The day of the week should always be in lowercase, 3-letter shortened as mon, tue, wed, thu, fri.
Some courses can be for multiple days; copy them for each day they are on the menu.
Also tag the dish (e.g. italian, asian, swedish, husmanskost). A dish can have multiple tags.
Ignore non-menu content such as opening hours or addresses.
Return only CSV and follow the CSV schema from the system prompt.
"""
)
IMAGE_PROMPT = (
    "Parse the provided image content and extract the lunch menu for the current week. "
    "Use the context fields when present."
)


def _load_secret_value(secret_id: str) -> str | None:
    if secret_id in _OPENAI_SECRET_CACHE:
        return _OPENAI_SECRET_CACHE[secret_id]

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_id)
    if "SecretString" in response and response["SecretString"]:
        secret_value = response["SecretString"]
    else:
        binary = response.get("SecretBinary")
        if not binary:
            return None
        secret_value = base64.b64decode(binary).decode("utf-8")

    _OPENAI_SECRET_CACHE[secret_id] = secret_value
    return secret_value


def resolve_openai_api_key() -> str | None:
    direct = os.environ.get("OPENAI_API_KEY")
    if direct:
        return direct

    secret_id = os.environ.get("OPENAI_API_KEY_SECRET_ARN") or os.environ.get(
        "OPENAI_API_KEY_SECRET_NAME"
    )
    if not secret_id:
        return None

    secret_value = _load_secret_value(secret_id)
    if not secret_value:
        return None

    try:
        payload = json.loads(secret_value)
        if isinstance(payload, dict):
            return (
                payload.get("OPENAI_API_KEY")
                or payload.get("openai_api_key")
                or payload.get("api_key")
            )
    except json.JSONDecodeError:
        pass

    return secret_value


def resolve_max_tokens(restaurant_id: str | None):
    override_raw = os.environ.get("OPENAI_MAX_TOKENS_OVERRIDES")
    if override_raw:
        try:
            overrides = json.loads(override_raw)
            if overrides and restaurant_id and restaurant_id in overrides:
                return int(overrides[restaurant_id])
        except json.JSONDecodeError:
            pass
    return int(os.environ.get("OPENAI_MAX_TOKENS", "2000"))


def resolve_temperature() -> float | None:
    value = os.environ.get("OPENAI_TEMPERATURE")
    return float(value) if value is not None else None


def resolve_top_p() -> float | None:
    value = os.environ.get("OPENAI_TOP_P")
    return float(value) if value is not None else None


def build_openai_request(task: str, context: dict, payload: dict, model: str, max_tokens: int):
    if task == "html":
        user_prompt = HTML_PROMPT
        payload_block = payload.get("html", "")
    elif task == "image":
        user_prompt = IMAGE_PROMPT
        binary = payload.get("binary", b"")
        payload_block = {
            "image_bytes_base64": base64.b64encode(binary).decode("utf-8"),
            "image_bytes_len": len(binary),
        }
    else:
        raise ValueError(f"Unknown task: {task}")

    request = {
        "model": model,
        "max_output_tokens": max_tokens,
        #"text": {"format": {"type": "text"}, "verbosity": "low"},
        #"reasoning": {"effort": "low"},
        "text": {"format": {"type": "text"}},
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "prompt": user_prompt,
                        "context": context,
                        "payload": payload_block,
                    }
                ),
            },
        ],
        "metadata": {
            "task": task,
            "restaurant_id": context.get("restaurant_id"),
        },
    }
    temperature = resolve_temperature()
    top_p = resolve_top_p()
    if temperature is not None:
        request["temperature"] = temperature
    if top_p is not None:
        request["top_p"] = top_p
    return request


def validate_csv_response(csv_text: str, restaurant_id: str | None):
    errors = []
    try:
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
    except csv.Error as exc:
        errors.append(f"csv_parse_error: {exc}")
        rows = []

    if not rows:
        errors.append("csv_empty")
    else:
        header = rows[0]
        if header != ["day", "lunch", "price", "tags"]:
            errors.append(f"csv_header_invalid: {header}")

        for index, row in enumerate(rows[1:], start=2):
            if len(row) != 4:
                errors.append(f"row_{index}_field_count: {len(row)}")
                continue
            day, lunch, price, tags = row
            if day not in {"mon", "tue", "wed", "thu", "fri"}:
                errors.append(f"row_{index}_day_invalid: {day}")
            if not lunch.strip():
                errors.append(f"row_{index}_lunch_empty")
            if price.strip():
                try:
                    float(price)
                except ValueError:
                    errors.append(f"row_{index}_price_invalid: {price}")
            if tags.strip():
                for tag in tags.split(" | "):
                    if not tag or tag != tag.lower():
                        errors.append(f"row_{index}_tag_invalid: {tag}")

    if errors:
        print(
            "OpenAI CSV validation failed",
            {"restaurant_id": restaurant_id, "errors": errors, "csv": csv_text},
        )
        raise ValueError("OpenAI CSV validation failed")


def _extract_response_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]
    if isinstance(payload.get("text"), str) and payload["text"].strip():
        return payload["text"]
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if isinstance(item.get("text"), str) and item["text"].strip():
                return item["text"]
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    return content["text"]
    choices = payload.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            message = choice.get("message", {})
            if message.get("content"):
                return message["content"]
    print(
        "OpenAI response missing output text",
        {"payload_keys": list(payload.keys()), "payload": payload},
    )
    raise ValueError("OpenAI response missing output text")


def query_chatgpt(task: str, context: dict, payload: dict):
    api_key = resolve_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to query OpenAI")

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    max_tokens = resolve_max_tokens(context.get("restaurant_id"))
    request = build_openai_request(task, context, payload, model, max_tokens)
    print(
        "OpenAI request prepared",
        {
            "task": task,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": request.get("temperature"),
            "top_p": request.get("top_p"),
        },
    )

    body = json.dumps(request).encode("utf-8")
    http_request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(http_request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(
            "OpenAI request failed",
            {"status": exc.code, "body": error_body[:2000]},
        )
        raise

    payload = json.loads(raw)
    text = _extract_response_text(payload).strip()
    return text


def parse_html_to_csv(_html: str, context: dict):
    csv_text = query_chatgpt("html", context, {"html": _html})
    validate_csv_response(csv_text, context.get("restaurant_id"))
    return csv_text


def parse_image_to_csv(_binary: bytes, context: dict):
    csv_text = query_chatgpt("image", context, {"binary": _binary})
    validate_csv_response(csv_text, context.get("restaurant_id"))
    return csv_text
