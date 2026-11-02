"""Helpers shared by the scrapers."""

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Retries slow or flaky government/UN sites a couple of times before giving up
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=2, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)))

_patterns = {}


def matches(text, keywords):
    """True if any keyword appears in text as a whole word (plurals allowed).

    Whole-word matching avoids false hits like "fund" in "fundamental".
    """
    if not text:
        return False
    key = tuple(keywords)
    if key not in _patterns:
        alternatives = "|".join(re.escape(k) for k in sorted(keywords, key=len, reverse=True))
        _patterns[key] = re.compile(rf"(?<!\w)(?:{alternatives})(?:s|es)?(?!\w)", re.I)
    return bool(_patterns[key].search(text))


def parse_date(value):
    """Parse a date string; returns a naive datetime or None."""
    if not value:
        return None
    # ISO dates first: dateutil with dayfirst would read 2026-11-09 as 11 Sep
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    try:
        return dateparser.parse(str(value), dayfirst=True, ignoretz=True)
    except (ValueError, OverflowError):
        return None


def is_open(deadline):
    """True if the deadline is unknown or has not passed yet."""
    parsed = deadline if isinstance(deadline, datetime) else parse_date(deadline)
    return parsed is None or parsed.date() >= datetime.now().date()


def format_date(value):
    """Format a deadline as e.g. "15 Nov 2026", or "Check listing" if unknown."""
    parsed = value if isinstance(value, datetime) else parse_date(value)
    return parsed.strftime("%d %b %Y") if parsed else "Check listing"


def fetch_rss(url, timeout=25):
    """Return [{title, link, summary, published}] for each item of an RSS feed."""
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "xml")
    items = []
    for item in soup.find_all("item"):
        title = item.find("title")
        link = item.find("link")
        summary = item.find("description")
        published = item.find("pubDate")
        items.append({
            "title": title.get_text(strip=True) if title else "",
            "link": link.get_text(strip=True) if link else "",
            # Descriptions are HTML; strip the tags
            "summary": BeautifulSoup(summary.get_text(), "html.parser").get_text(" ", strip=True) if summary else "",
            "published": parse_date(published.get_text(strip=True)) if published else None,
        })
    return items
