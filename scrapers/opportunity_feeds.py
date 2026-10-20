"""Grant, accelerator and funding-call feeds from opportunity aggregator sites (RSS)."""

import os
import sys
from datetime import datetime, timedelta

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import OPPORTUNITY_TYPES, FUNDING_TOPICS, REGIONS
from scrapers.common import matches, fetch_rss

FEEDS = {
    "fundsforNGOs": "https://www2.fundsforngos.org/feed/",
    "Opportunity Desk": "https://opportunitydesk.org/feed/",
    "Opportunities for Africans": "https://www.opportunitiesforafricans.com/feed/",
}

# The radar runs weekly, so read back a little over a week of posts.
# fundsforNGOs alone publishes ~75 posts a day, hence the high page cap.
LOOKBACK_DAYS = 8
MAX_PAGES = 40


def recent_items(url):
    """Read a WordPress feed page by page until posts are older than LOOKBACK_DAYS."""
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    items = []
    for page in range(1, MAX_PAGES + 1):
        try:
            page_items = fetch_rss(f"{url}?paged={page}")
        except requests.HTTPError:
            if page == 1:
                raise
            break  # past the last page
        if not page_items:
            break
        items.extend(i for i in page_items if not i["published"] or i["published"] >= cutoff)
        oldest = page_items[-1]["published"]
        if oldest and oldest < cutoff:
            break
    return items


def fetch():
    """Fetch recent grants / accelerators / funding calls open to an African tech company.

    An item must name an opportunity type in its title (grant, accelerator, ...),
    and its title or summary must mention a tech topic and a region Kamagram qualifies for.
    """
    results = []

    for name, url in FEEDS.items():
        try:
            items = recent_items(url)
        except requests.RequestException as e:
            print(f"[Feeds] Error fetching {name}: {e}")
            continue

        count = 0
        for item in items:
            title = item["title"]
            text = f"{title} {item['summary']}"
            if not (matches(title, OPPORTUNITY_TYPES)
                    and matches(text, FUNDING_TOPICS)
                    and matches(text, REGIONS)):
                continue
            if not item["link"]:
                continue

            results.append({
                "title": title[:200],
                "org": name,
                "deadline": "Check listing",
                "link": item["link"],
                "source": name,
            })
            count += 1

        print(f"[Feeds] {name}: {count} matches from {len(items)} recent posts")

    return results


if __name__ == "__main__":
    for t in fetch():
        print(f"  - [{t['source']}] {t['title'][:80]}")
