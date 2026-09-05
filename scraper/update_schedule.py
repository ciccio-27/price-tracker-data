"""
Computes the optimal check frequency based on the number of tracked products
and writes it to data/schedule.json.

The workflow runs on a fixed hourly cron; track.py reads schedule.json at
runtime to decide whether this particular hour/day is actually a run slot,
so we never need to touch the workflow YAML (which would require the special
`workflows` GitHub token permission).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_FILE = ROOT / "data" / "products.json"
SCHEDULE_FILE = ROOT / "data" / "schedule.json"


def get_cron_for_count(count):
    if count == 0:
        return "0 6 * * *"

    # Tavily limit: 1000/month. Safe limit: 900/month to leave room for manual adds.
    monthly_runs = 900 // count

    if monthly_runs >= 30:
        return "0 6 * * *"       # Every day
    elif monthly_runs >= 15:
        return "0 6 */2 * *"     # Every 2 days
    elif monthly_runs >= 10:
        return "0 6 */3 * *"     # Every 3 days
    elif monthly_runs >= 7:
        return "0 6 */4 * *"     # Every 4 days
    elif monthly_runs >= 4:
        return "0 6 * * 0"       # Once a week
    elif monthly_runs >= 2:
        return "0 6 1,15 * *"    # Twice a month
    else:
        return "0 6 1 * *"       # Once a month


def main():
    if not PRODUCTS_FILE.exists():
        return

    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    count = len(products)
    cron = get_cron_for_count(count)

    schedule = {"cron": cron, "product_count": count}

    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2)

    print(f"Schedule set to: {cron} (for {count} products) -> data/schedule.json")


if __name__ == "__main__":
    main()
