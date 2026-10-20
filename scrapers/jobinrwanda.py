import requests
from bs4 import BeautifulSoup
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KEYWORDS

BASE_URL = "https://www.jobinrwanda.com"


def fetch():
    """Fetch tenders/jobs from JobInRwanda that match our keywords."""
    results = []

    # Try different category pages (correct paths found from site)
    urls_to_try = [
        f"{BASE_URL}/jobs/tender",       # Tenders category
        f"{BASE_URL}/jobs/consultancy",  # Consultancy opportunities
        f"{BASE_URL}/jobs/all",          # All jobs
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
                title_lower = title_text.lower()
                if any(k.lower() in title_lower for k in KEYWORDS):
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

                        # Look for deadline info
                        deadline_elem = container.find(string=re.compile(r"deadline", re.I))
                        if deadline_elem:
                            deadline = str(deadline_elem).strip()[:30]

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
