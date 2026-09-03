"""
Given a product name, finds candidate seller pages on the web (via the
Tavily search API's free tier) and prices each one using the same
structured-data extractor as before. Returns a list of offers sorted by
price, ascending — this is what powers the idealo-style comparison table.

We deliberately skip aggregator/marketplace sites we don't want to re-scrape
(they either block bots harder or would just duplicate another retailer's
price) and any obviously irrelevant domains.
"""
import os
from urllib.parse import urlparse

import requests

from scrapers.generic import fetch_price

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"

# Sites to skip: aggregators (they don't sell directly), and generic noise.
EXCLUDED_DOMAINS = {
    "idealo.it", "idealo.com", "trovaprezzi.it", "kelkoo.it",
    "wikipedia.org", "youtube.com", "reddit.com", "facebook.com",
    "instagram.com", "pinterest.com", "twitter.com", "x.com",
}


def _domain(url):
    return urlparse(url).netloc.replace("www.", "")


def search_candidate_urls(query, max_results=20):
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not set")

    resp = requests.post(
        TAVILY_URL,
        json={
            "api_key": TAVILY_API_KEY,
            "query": f"{query} prezzo acquista",
            "search_depth": "basic",
            "max_results": max_results,
            "include_raw_content": true
        },
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])

    candidates = []
    for r in results:
        url = r.get("url")
        if not url:
            continue
        domain = _domain(url)
        if any(domain == bad or domain.endswith("." + bad) for bad in EXCLUDED_DOMAINS):
            continue
        candidates.append((url, domain, r.get("title", "")))
    return candidates


def find_offers(query, max_results=20):
    """Returns offers sorted by price ascending, one entry per domain
    (cheapest kept if a domain shows up twice)."""
    best_by_domain = {}

    for url, domain, title in search_candidate_urls(query, max_results=max_results):
        try:
            price = fetch_price(url)
        except Exception:
            continue
        if price is None:
            continue
        if domain not in best_by_domain or price < best_by_domain[domain]["price"]:
            best_by_domain[domain] = {
                "domain": domain,
                "url": url,
                "title": title,
                "price": price,
            }

    return sorted(best_by_domain.values(), key=lambda o: o["price"])
