import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_FILE = ROOT / "data" / "products.json"
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "check-prices.yml"

def get_cron_for_count(count):
    if count == 0:
        return "0 6 * * *"
        
    # Tavily limit: 1000/month. Safe limit: 900/month to leave room for manual adds.
    monthly_runs = 900 // count
    
    if monthly_runs >= 30:
        return "0 6 * * *" # Every day
    elif monthly_runs >= 15:
        return "0 6 */2 * *" # Every 2 days
    elif monthly_runs >= 10:
        return "0 6 */3 * *" # Every 3 days
    elif monthly_runs >= 7:
        return "0 6 */4 * *" # Every 4 days
    elif monthly_runs >= 4:
        return "0 6 * * 0" # Once a week
    elif monthly_runs >= 2:
        return "0 6 1,15 * *" # Twice a month
    else:
        return "0 6 1 * *" # Once a month

def main():
    if not PRODUCTS_FILE.exists():
        return
        
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)
        
    count = len(products)
    new_cron = get_cron_for_count(count)
    
    if not WORKFLOW_FILE.exists():
        return
        
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        
    new_content = re.sub(r'- cron: ".*?"', f'- cron: "{new_cron}"', content)
    
    if new_content != content:
        with open(WORKFLOW_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated schedule to: {new_cron} (for {count} products)")
    else:
        print(f"Schedule is already optimal: {new_cron} (for {count} products)")

if __name__ == "__main__":
    main()
