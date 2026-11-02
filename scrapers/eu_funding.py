"""EU Funding & Tenders portal (public SEDIA search API), Africa-related calls."""

import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import FUNDING_TOPICS, TARGET_COUNTRIES
from scrapers.common import SESSION, matches, is_open, format_date, parse_date

# "SEDIA" is the portal's own public API key
API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA"
TOPIC_URL = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{id}"

# Result types: 1 = grant topic, 2 = tender, 8 = cascade funding (third-party calls)
TYPES = ["1", "2", "8"]
# Statuses: 31094501 = forthcoming, 31094502 = open
STATUSES = ["31094501", "31094502"]

SEARCH_TERMS = ["Africa"] + TARGET_COUNTRIES


def _first(metadata, key):
    values = metadata.get(key) or [""]
    return values[0] if isinstance(values, list) else values


def fetch():
    """Fetch open or forthcoming EU calls about Africa that involve tech/digital work."""
    results = []
    seen = set()
    query = {"bool": {"must": [{"terms": {"type": TYPES}}, {"terms": {"status": STATUSES}}]}}

    for term in SEARCH_TERMS:
        try:
            r = SESSION.post(
                f"{API_URL}&text={requests.utils.quote(term)}&pageSize=100&pageNumber=1",
                files={
                    "query": ("blob", json.dumps(query), "application/json"),
                    "languages": ("blob", json.dumps(["en"]), "application/json"),
                },
                timeout=30,
            )
            r.raise_for_status()
            items = r.json().get("results", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[EUFunding] Error searching '{term}': {e}")
            continue

        for x in items:
            md = x.get("metadata", {})
            identifier = _first(md, "identifier")
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)

            title = _first(md, "title") or x.get("summary") or ""
            keywords = " ".join(md.get("keywords") or [])
            if not matches(f"{title} {keywords}", FUNDING_TOPICS):
                continue

            # Some calls have several cut-off dates; the latest one decides if it's still open
            deadlines = [d for d in (parse_date(v) for v in md.get("deadlineDate") or []) if d]
            deadline = max(deadlines) if deadlines else None
            if not is_open(deadline):
                continue

            link = TOPIC_URL.format(id=identifier) if _first(md, "type") == "1" else x.get("url", "")
            results.append({
                "title": title.strip()[:200],
                "org": "European Commission",
                "deadline": format_date(deadline),
                "link": link,
                "source": "EU Funding & Tenders",
            })

    print(f"[EUFunding] {len(results)} matches from {len(seen)} open Africa-related calls")
    return results


if __name__ == "__main__":
    for t in fetch():
        print(f"  - {t['title'][:70]} | {t['deadline']} | {t['link']}")
