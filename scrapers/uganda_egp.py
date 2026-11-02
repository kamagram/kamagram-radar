"""Uganda Electronic Government Procurement (egpuganda.go.ug) bid notices."""

import os
import sys

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KEYWORDS
from scrapers.common import SESSION, matches, is_open, format_date

BID_NOTICES_URL = "https://egpuganda.go.ug/bid-notices"


def fetch():
    """Fetch open Ugandan government bid notices that match our keywords.

    The listing truncates long subjects (~45 characters), so matching only sees
    the start of each title.
    """
    results = []

    try:
        r = SESSION.get(BID_NOTICES_URL, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[UgandaEGP] Error fetching {BID_NOTICES_URL}: {e}")
        return results

    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("table tr")[1:]  # skip header

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        subject = cells[2].get_text(" ", strip=True).rstrip(".").strip()
        if not matches(subject, KEYWORDS):
            continue
        deadline = cells[4].get_text(strip=True)
        if not is_open(deadline):
            continue

        link_elem = cells[0].find("a", href=True)
        org_elem = cells[0].select_one(".text-muted")
        category = cells[1].get_text(strip=True)

        results.append({
            "title": f"{subject} ({category})" if category else subject,
            "org": org_elem.get_text(strip=True) if org_elem else "Uganda Government",
            "deadline": format_date(deadline),
            "link": link_elem["href"] if link_elem else BID_NOTICES_URL,
            "source": "Uganda eGP",
        })

    print(f"[UgandaEGP] {len(results)} matches from {len(rows)} bid notices")
    return results


if __name__ == "__main__":
    for t in fetch():
        print(f"  - {t['title'][:70]} | {t['org']} | {t['deadline']}")
