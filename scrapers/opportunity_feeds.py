"""Grant, accelerator and funding-call feeds from opportunity aggregator sites (RSS)."""

import os
import sys
import time
from datetime import datetime, timedelta

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import OPPORTUNITY_TYPES, FUNDING_TOPICS, REGIONS
from scrapers.common import SESSION, matches, fetch_rss

FEEDS = {
    "fundsforNGOs": "https://www2.fundsforngos.org/feed/",
    "Opportunity Desk": "https://opportunitydesk.org/feed/",
    "Opportunities for Africans": "https://www.opportunitiesforafricans.com/feed/",
}

# The radar runs weekly, so read back a little over a week of posts.
# fundsforNGOs alone publishes ~75 posts a day, hence the high page cap.
LOOKBACK_DAYS = 8
MAX_PAGES = 40


def fetch_page(url):
    """Fetch one feed page, retrying once with fresh cookies.

    fundsforNGOs sits behind Cloudflare, which now and then sends GitHub's
    servers round a redirect loop; a second try with new cookies usually works.
    """
    try:
        return fetch_rss(url)
    except requests.TooManyRedirects:
        SESSION.cookies.clear()
        time.sleep(5)
        return fetch_rss(url)


def recent_items(name, url):
    """Read a WordPress feed page by page until posts are older than LOOKBACK_DAYS."""
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    items = []
    for page in range(1, MAX_PAGES + 1):
        # Page 1 is the plain feed URL; ?paged=1 only redirects back to it
        page_url = url if page == 1 else f"{url}?paged={page}"
        try:
            page_items = fetch_page(page_url)
        except requests.HTTPError:
            if page == 1:
                raise
            break  # past the last page
        except requests.RequestException as e:
            if page == 1:
                raise
            # Keep the pages already read rather than losing the whole feed
            print(f"[Feeds] {name}: stopped at page {page} ({e}); keeping {len(items)} posts")
            break
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
            items = recent_items(name, url)
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
