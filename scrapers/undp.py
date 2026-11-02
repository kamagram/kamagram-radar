"""UNDP procurement notices (procurement-notices.undp.org), Africa region."""

import os
import re
import sys

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KEYWORDS, OPPORTUNITY_TYPES, FUNDING_TOPICS
from scrapers.common import SESSION, matches, is_open, format_date

BASE_URL = "https://procurement-notices.undp.org/"
AFRICA_REGION = "region_RAF"


def fetch():
    """Fetch open UNDP notices in Africa: tech RFPs plus tech innovation challenges."""
    results = []

    try:
        r = SESSION.get(BASE_URL, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[UNDP] Error fetching {BASE_URL}: {e}")
        return results

    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("a.vacanciesTableLink")
    africa_rows = [row for row in rows if row.get("data-region") == AFRICA_REGION]

    for row in africa_rows:
        # Each cell is a label div followed by a value span
        cells = {}
        for cell in row.select(".vacanciesTable__cell"):
            label = cell.select_one(".vacanciesTable__cell__label")
            value = cell.find("span")
            if label and value:
                cells[label.get_text(strip=True)] = value.get_text(" ", strip=True)

        title = cells.get("Title", "")
        process = cells.get("Process", "")
        is_tech_rfp = matches(title, KEYWORDS)
        is_tech_call = matches(f"{title} {process}", OPPORTUNITY_TYPES) and matches(title, FUNDING_TOPICS)
        if not (is_tech_rfp or is_tech_call):
            continue
        # e.g. "30-Oct-26 07:00 AM (New York time)" - drop the timezone note so it parses
        deadline = re.sub(r"\(.*?\)", "", cells.get("Deadline", "")).strip()
        if not is_open(deadline):
            continue

        office = cells.get("UNDP Office/Country", "UNDP")
        results.append({
            "title": f"{title[:180]} ({process})" if process else title[:200],
            "org": office,
            "deadline": format_date(deadline),
            "link": BASE_URL + row.get("href", ""),
            "source": "UNDP Procurement",
        })

    print(f"[UNDP] {len(results)} matches from {len(africa_rows)} Africa notices ({len(rows)} worldwide)")
    return results


if __name__ == "__main__":
    for t in fetch():
        print(f"  - {t['title'][:70]} | {t['org']} | {t['deadline']}")
