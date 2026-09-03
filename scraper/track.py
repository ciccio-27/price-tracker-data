"""
Runs once per invocation (GitHub Actions calls this on a schedule).

For every tracked product name in public/data/products.json:
  - search the web for sellers and price each candidate page
  - save the full set of offers (for the comparison table)
  - append the best price found to price_history.json (for the trend line)
  - if the best price is at or below the target, send an email alert

All three files are committed back to the repo by the workflow.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from search import find_offers  # noqa: E402
from notify import send_email  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_FILE = ROOT / "data" / "products.json"
HISTORY_FILE = ROOT / "data" / "price_history.json"
OFFERS_FILE = ROOT / "data" / "offers.json"
ACTIONS_FILE = ROOT / "data" / "actions.json"


def load_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    products = load_json(PRODUCTS_FILE, [])
    history = load_json(HISTORY_FILE, {})
    offers_data = load_json(OFFERS_FILE, {})
    actions = load_json(ACTIONS_FILE, [])
    successful_products = []
    number = len(products)

    if not products:
        print("No products to check yet.")
        return

    now = datetime.now(timezone.utc).isoformat()

    for product in products:
        pid = product["id"]
        name = product.get("name", pid)
        target_price = product.get("target_price")

        print(f"Searching offers for '{name}' ...")
        try:
            offers = find_offers(name)
        except Exception as exc:
            print(f"  search failed: {exc}")
            continue

        if not offers:
            print("  no offers found this time")
            continue

        offers_data[pid] = {"checked_at": now, "offers": offers}
        successful_products.append(name)

        best = offers[0]
        history.setdefault(pid, [])
        history[pid].append({"date": now, "price": best["price"]})
        print(f"  best price: {best['price']} at {best['domain']} ({len(offers)} sellers found)")

        if target_price is not None and best["price"] <= float(target_price):
            offer_lines = "\n".join(
                f"- {o['domain']}: {o['price']}  {o['url']}" for o in offers[:5]
            )
            send_email(
                subject=f"Price drop: {name}",
                message=(
                    f"Best price for {name} is now {best['price']} at "
                    f"{best['domain']} (your target was {target_price}).\n\n"
                    f"Top offers:\n{offer_lines}"
                ),
            )

    save_json(HISTORY_FILE, history)
    save_json(OFFERS_FILE, offers_data)
    
    actions.append({
        "timestamp": now,
        "successful_searches": successful_products
    })
    save_json(ACTIONS_FILE, actions)
    print("Done.")


if __name__ == "__main__":
    main()
