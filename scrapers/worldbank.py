"""World Bank procurement notices (official JSON API, no key needed)."""

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KEYWORDS, TARGET_COUNTRIES
from scrapers.common import SESSION, matches, is_open, format_date

API_URL = "https://search.worldbank.org/api/v2/procnotices"
NOTICE_URL = "https://projects.worldbank.org/en/projects-operations/procurement-detail/{id}"

# Award notices are for contracts already given out
SKIP_NOTICE_TYPES = {"Contract Award"}


def fetch():
    """Fetch open World Bank-funded procurement notices for Kamagram's countries."""
    results = []

    for country in TARGET_COUNTRIES:
        params = {
            "format": "json",
            "rows": 200,
            "srt": "submission_date",
            "order": "desc",
            "project_ctry_name_exact": country,
        }
        try:
            r = SESSION.get(API_URL, params=params, timeout=30)
            r.raise_for_status()
            notices = r.json().get("procnotices", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[WorldBank] Error fetching {country}: {e}")
            continue

        count = 0
        for n in notices:
            if n.get("notice_type") in SKIP_NOTICE_TYPES:
                continue
            description = n.get("bid_description") or ""
            if not matches(description, KEYWORDS):
                continue
            deadline = n.get("submission_deadline_date")
            if not is_open(deadline):
                continue

            results.append({
                "title": f"{description.strip()[:180]} ({country})",
                "org": n.get("project_name") or "World Bank",
                "deadline": format_date(deadline),
                "link": NOTICE_URL.format(id=n["id"]),
                "source": f"World Bank - {n.get('notice_type', 'Notice')}",
            })
            count += 1

        print(f"[WorldBank] {country}: {count} matches from {len(notices)} recent notices")

    return results


if __name__ == "__main__":
    for t in fetch():
        print(f"  - {t['title'][:70]} | {t['deadline']} | {t['link']}")
