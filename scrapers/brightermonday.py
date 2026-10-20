import requests
from bs4 import BeautifulSoup
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KEYWORDS

# BrighterMonday sites for East Africa
SITES = {
    "Kenya": "https://www.brightermonday.co.ke",
    "Uganda": "https://www.brightermonday.co.ug",
    "Tanzania": "https://www.brightermonday.co.tz",
}

# Job category paths
CATEGORY_PATHS = [
    "/jobs/software-data",
    "/jobs/it-telecoms",
    "/jobs?q=software+developer",
    "/jobs?q=web+developer",
]


def fetch():
    """Fetch IT/software jobs from BrighterMonday East Africa."""
    results = []
    seen_links = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for country, base_url in SITES.items():
        country_count = 0
        for path in CATEGORY_PATHS:
            url = base_url + path
            try:
                r = requests.get(url, timeout=20, headers=headers, allow_redirects=True)
                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "html.parser")

                # Find job cards by data-cy attribute
                job_cards = soup.select('[data-cy="listing-cards-components"]')

                for card in job_cards:
                    try:
                        # Find the title link
                        title_link = card.select_one('a[data-cy="listing-title-link"]')
                        if not title_link:
                            title_link = card.select_one('a[href*="/listings/"]')

                        if not title_link:
                            continue

                        href = title_link.get("href", "")
                        if not href:
                            continue

                        # Build full link
                        if href.startswith("/"):
                            full_link = base_url + href
                        elif href.startswith("http"):
                            full_link = href
                        else:
                            continue

                        if full_link in seen_links:
                            continue

                        # Get title text
                        title_elem = title_link.select_one("p") or title_link
                        title_text = title_elem.get_text(strip=True)

                        if not title_text:
                            continue

                        # Check keyword match
                        title_lower = title_text.lower()
                        if not any(k.lower() in title_lower for k in KEYWORDS):
                            continue

                        seen_links.add(full_link)

                        # Get company name
                        org = f"BrighterMonday {country}"
                        company_elem = card.select_one('p.text-blue-700, p.text-sm.text-blue-700')
                        if company_elem:
                            company_text = company_elem.get_text(strip=True)
                            if company_text and company_text != title_text:
                                org = company_text

                        # Get location/deadline info
                        deadline = "Check listing"
                        location_elem = card.select_one('span.bg-brand-secondary-100')
                        if location_elem:
                            deadline = location_elem.get_text(strip=True)

                        results.append({
                            "title": title_text[:200],
                            "org": org,
                            "deadline": deadline,
                            "link": full_link,
                            "source": f"BrighterMonday {country}"
                        })
                        country_count += 1

                    except Exception as e:
                        continue

            except requests.RequestException as e:
                print(f"[BrighterMonday] Error fetching {url}: {e}")
                continue

        print(f"[BrighterMonday] {country}: {country_count} matches")

    print(f"[BrighterMonday] Total: {len(results)} matches")
    return results


if __name__ == "__main__":
    tenders = fetch()
    print(f"\nFound {len(tenders)} matching listings:")
    for t in tenders:
        print(f"  - {t['title'][:60]}...")
        print(f"    Org: {t['org']}")
        print(f"    Link: {t['link']}")
