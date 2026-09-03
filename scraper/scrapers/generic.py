"""
Generic price extractor.

Strategy, in order:
1. Look for schema.org JSON-LD ("Product" -> "offers" -> "price"). Most modern
   e-commerce sites (including many built on Shopify, WooCommerce, etc.)
   include this, so no site-specific code is needed.
2. Look for common meta tags (og:price:amount, product:price:amount).
3. Fall back to a CSS selector you provide per-product (for sites without
   structured data). You find this selector once, manually, using your
   browser's "inspect element" on the price.

This keeps most products "zero config" and only asks you to babysit the
stubborn ones.
"""
import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

MONTHLY_MARKERS = [
    "/mese",
    "al mese",
    "mensil",
    "rate",
    "rateiz",
    "finanziament",
    "tan",
    "taeg"
]

EURO_PRICE_RE = re.compile(r"€\s?(\d{1,4}(?:[.,]\d{1,2})?)|(\d{1,4}(?:[.,]\d{1,2})?)\s?€")
PURE_NUMBER_RE = re.compile(r"^\s*(\d+(?:[.,]\d{1,2})?)\s*$")


def _clean_price(raw):
    if raw is None:
        return None
    raw = str(raw).replace("\xa0", " ")
    
    # 1. Check if it's a pure number (from JSON-LD or meta tags)
    pure_match = PURE_NUMBER_RE.match(raw)
    if pure_match:
        try:
            return float(pure_match.group(1).replace(",", "."))
        except ValueError:
            return None

    # 2. Extract from page text looking for euro symbols
    valid_prices = []
    
    for match in EURO_PRICE_RE.finditer(raw):
        num_str = match.group(1) or match.group(2)
        try:
            price_val = float(num_str.replace(",", "."))
        except ValueError:
            continue
            
        # Check the ~40 characters immediately following this match
        end_idx = match.end()
        following_text = raw[end_idx : end_idx + 40].lower()
        
        is_monthly = False
        for marker in MONTHLY_MARKERS:
            if marker in following_text:
                is_monthly = True
                break
                
        if not is_monthly:
            valid_prices.append(price_val)
            
    if not valid_prices:
        return None
        
    return min(valid_prices)


def _from_jsonld(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "Product" and "offers" in item:
                offers = item["offers"]
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                price = offers.get("price") or offers.get("lowPrice")
                cleaned = _clean_price(price)
                if cleaned:
                    return cleaned
    return None


def _from_meta(soup):
    for prop in ("product:price:amount", "og:price:amount"):
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            cleaned = _clean_price(tag["content"])
            if cleaned:
                return cleaned
    return None


def _from_selector(soup, selector):
    if not selector:
        return None
    el = soup.select_one(selector)
    if not el:
        return None
    return _clean_price(el.get_text())


def fetch_price(url, selector=None, timeout=15):
    """Returns a float price, or None if it couldn't be determined."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for extractor in (_from_jsonld, _from_meta):
        price = extractor(soup)
        if price is not None:
            return price

    return _from_selector(soup, selector)
