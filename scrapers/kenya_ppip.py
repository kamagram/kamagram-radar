"""Kenya Public Procurement Information Portal (tenders.go.ke JSON API)."""

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KEYWORDS
from scrapers.common import SESSION, matches, is_open, format_date

API_URL = "https://tenders.go.ke/api/active-tenders"
TENDER_URL = "https://tenders.go.ke/tenders/{id}"
PER_PAGE = 200
MAX_PAGES = 10


def fetch():
    """Fetch active Kenyan government tenders that match our keywords."""
    results = []
    checked = 0

    for page in range(1, MAX_PAGES + 1):
        try:
            r = SESSION.get(API_URL, params={"perpage": PER_PAGE, "page": page},
                             headers={"Accept": "application/json"}, timeout=60)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"[KenyaPPIP] Error fetching page {page}: {e}")
            break

        for t in data.get("data", []):
            checked += 1
            title = t.get("title") or ""
            if not matches(title, KEYWORDS) or not is_open(t.get("close_at")):
                continue
            pe = t.get("pe") or {}
            results.append({
                "title": title.strip()[:200],
                "org": pe.get("name") or "Kenya Government",
                "deadline": format_date(t.get("close_at")),
                "link": TENDER_URL.format(id=t["id"]),
                "source": "Kenya PPIP",
            })

        if page >= (data.get("last_page") or 1):
            break

    print(f"[KenyaPPIP] {len(results)} matches from {checked} active tenders")
    return results


if __name__ == "__main__":
    for t in fetch():
        print(f"  - {t['title'][:70]} | {t['org']} | {t['deadline']}")
