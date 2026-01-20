import json
import os

DEFAULT_MODEL = "gpt-5-nano"


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


def parse_html_to_csv(_html: str, context: dict):
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to parse HTML menus")

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    max_tokens = resolve_max_tokens(context.get("restaurant_id"))
    print("OpenAI parse HTML", {"model": model, "max_tokens": max_tokens})

    raise NotImplementedError("OpenAI HTML parsing not implemented yet")


def parse_image_to_csv(_binary: bytes, context: dict):
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to parse image menus")

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    max_tokens = resolve_max_tokens(context.get("restaurant_id"))
    print("OpenAI parse image", {"model": model, "max_tokens": max_tokens})

    raise NotImplementedError("OpenAI image parsing not implemented yet")
