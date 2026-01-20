import re
from datetime import datetime, timezone


_WEEKLY_KEY_RE = re.compile(r"^weekly/year=(\d{4})/week=(\d{2})/(.+)\.csv$")


def build_weekly_key(restaurant_id: str, date: datetime | None = None) -> str:
    current = date or datetime.now(timezone.utc)
    year, week, _ = current.isocalendar()
    return f"weekly/year={year}/week={week:02d}/{restaurant_id}.csv"


def parse_weekly_key(key: str):
    match = _WEEKLY_KEY_RE.match(key)
    if not match:
        return None
    return {
        "year": match.group(1),
        "week": match.group(2),
        "restaurant_id": match.group(3),
    }
