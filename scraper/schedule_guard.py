"""
Reads data/schedule.json and checks whether the current UTC datetime
matches the stored cron expression so track.py can skip runs that fall
outside the computed schedule.

Supported cron fields (minute, hour, day-of-month, month, day-of-week).
Only the simple patterns produced by update_schedule.py are handled:
  - exact values  (e.g. "6")
  - step values   (e.g. "*/2", "*/3")
  - lists         (e.g. "1,15")
  - wildcards     ("*")
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_FILE = ROOT / "data" / "schedule.json"


def _field_matches(field: str, value: int) -> bool:
    """Return True if *value* satisfies the cron *field* expression."""
    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return value % step == 0
    if "," in field:
        return value in {int(v) for v in field.split(",")}
    return int(field) == value


def should_run(now: datetime | None = None) -> bool:
    """
    Return True if the current time matches the schedule stored in
    data/schedule.json.  If the file does not exist, always return True
    (fail open so the first run after bootstrap still works).
    """
    if not SCHEDULE_FILE.exists():
        return True

    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cron = data.get("cron", "")
    if not cron:
        return True

    parts = cron.split()
    if len(parts) != 5:
        return True  # unrecognised format — fail open

    minute_f, hour_f, dom_f, month_f, dow_f = parts

    if now is None:
        now = datetime.now(timezone.utc)

    return (
        _field_matches(minute_f, now.minute)
        and _field_matches(hour_f, now.hour)
        and _field_matches(dom_f, now.day)
        and _field_matches(month_f, now.month)
        and _field_matches(dow_f, now.weekday())  # 0=Monday in Python; cron 0=Sunday
    )
