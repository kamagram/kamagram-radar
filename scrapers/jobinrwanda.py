import requests
from bs4 import BeautifulSoup
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KEYWORDS
from scrapers.common import matches, is_open, format_date

BASE_URL = "https://www.jobinrwanda.com"


def fetch():
    """Fetch tenders and consultancies from JobInRwanda that match our keywords."""
    results = []

    # Tender and consultancy categories only (regular job ads are skipped)
    urls_to_try = [
        f"{BASE_URL}/jobs/tender",       # Tenders category
        f"{BASE_URL}/jobs/consultancy",  # Consultancy opportunities
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    seen_links = set()

    for url in urls_to_try:
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200:
                print(f"[JobInRwanda] {url} returned {r.status_code}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")

            # Find job cards by the h5.card-title selector
            cards = soup.select("h5.card-title")

            for card in cards:
                # Get the parent link
                parent_link = card.find_parent("a")
                if not parent_link:
                    continue

                href = parent_link.get("href", "")
                if not href or href in seen_links:
                    continue

                seen_links.add(href)
                title_text = card.get_text(strip=True)

                if not title_text:
                    continue

                # Check if any keyword matches
                if matches(title_text, KEYWORDS):
                    # Build full link
                    if href.startswith("/"):
                        full_link = BASE_URL + href
                    elif href.startswith("http"):
                        full_link = href
                    else:
                        full_link = BASE_URL + "/" + href

                    # Try to find org and deadline from the card's container
                    container = card.find_parent(["div", "article"])
                    org = "JobInRwanda"
                    deadline = "Check listing"

                    if container:
                        # Look for employer link
                        employer_link = container.find("a", href=re.compile(r"/employer/"))
                        if employer_link:
                            org = employer_link.get_text(strip=True)

                        # The deadline is the <time> tag after "Deadline"
                        # (the text before it is the location and publish date)
                        deadline_elem = container.find("time")
                        if deadline_elem:
                            deadline_value = deadline_elem.get("datetime") or deadline_elem.get_text(strip=True)
                            if not is_open(deadline_value):
                                continue
                            deadline = format_date(deadline_value)

                    results.append({
                        "title": title_text,
                        "org": org,
                        "deadline": deadline,
                        "link": full_link,
                        "source": "JobInRwanda"
                    })

            print(f"[JobInRwanda] {url}: {len(results)} matches total")

        except requests.RequestException as e:
            print(f"[JobInRwanda] Error fetching {url}: {e}")
            continue

    return results


if __name__ == "__main__":
    # Test the scraper
    tenders = fetch()
    print(f"\nFound {len(tenders)} matching listings:")
    for t in tenders:
        print(f"  - {t['title'][:60]}...")
        print(f"    Link: {t['link']}")
