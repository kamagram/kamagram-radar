#!/usr/bin/env python3
"""
Kamagram Tender Radar
=====================
Automatically monitors RFP/tender portals and grant, accelerator and funding
feeds for opportunities relevant to Kamagram, and sends email alerts.

Usage:
    python radar.py              # Run full scan and send email
    python radar.py --dry-run    # Run scan without sending email
    python radar.py --list       # List all tenders in database
"""

import argparse
from datetime import datetime

from db import init_db, save_tender, get_unsent, mark_sent, get_all_tenders
from scrapers import (
    jobinrwanda, worldbank, kenya_ppip, uganda_egp, undp, eu_funding, opportunity_feeds,
    devex, tenderafrica, reliefweb, google_search,
)
from config import SOURCES
from emailer import send_email


# (SOURCES key, display name, module)
SCRAPERS = [
    ("jobinrwanda", "JobInRwanda", jobinrwanda),
    ("worldbank", "World Bank", worldbank),
    ("kenya_ppip", "Kenya PPIP", kenya_ppip),
    ("uganda_egp", "Uganda eGP", uganda_egp),
    ("undp", "UNDP", undp),
    ("eu_funding", "EU Funding & Tenders", eu_funding),
    ("opportunity_feeds", "grant & accelerator feeds", opportunity_feeds),
    ("devex", "Devex", devex),
    ("tenderafrica", "TenderAfrica", tenderafrica),
    ("reliefweb", "ReliefWeb", reliefweb),
    ("google_search", "Google Custom Search", google_search),
]


def run_scrapers():
    """Run all enabled scrapers and return results."""
    all_tenders = []

    for key, name, module in SCRAPERS:
        if not SOURCES.get(key):
            continue
        print(f"[Scraper] Fetching from {name}...")
        try:
            tenders = module.fetch()
        except Exception as e:
            # One broken source shouldn't stop the others
            print(f"[Scraper] {name} failed: {e}")
            continue
        print(f"[Scraper] Found {len(tenders)} matching opportunities from {name}")
        all_tenders.extend(tenders)

    return all_tenders


def save_tenders(tenders):
    """Save tenders to database, return count of new ones."""
    new_count = 0
    for t in tenders:
        if save_tender(t):
            new_count += 1
            print(f"[DB] New tender saved: {t['title'][:50]}...")
    return new_count


def main():
    parser = argparse.ArgumentParser(description="Kamagram Tender Radar")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending email")
    parser.add_argument("--list", action="store_true", help="List all tenders in database")
    args = parser.parse_args()

    print("=" * 60)
    print("Kamagram Tender Radar")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Initialize database
    init_db()

    # List mode
    if args.list:
        tenders = get_all_tenders()
        print(f"\nTotal tenders in database: {len(tenders)}\n")
        for t in tenders:
            sent_status = "SENT" if t[6] else "PENDING"
            print(f"[{sent_status}] {t[1][:50]}...")
            print(f"         Source: {t[5]} | Deadline: {t[3]}")
            print(f"         Link: {t[4]}")
            print()
        return

    # Run scrapers
    print("\n[Step 1] Running scrapers...")
    tenders = run_scrapers()
    print(f"Total tenders found: {len(tenders)}")

    # Save to database
    print("\n[Step 2] Saving to database...")
    new_count = save_tenders(tenders)
    print(f"New tenders saved: {new_count}")

    # Get unsent tenders
    print("\n[Step 3] Checking for unsent tenders...")
    unsent = get_unsent()
    print(f"Unsent tenders: {len(unsent)}")

    if not unsent:
        print("\n[Done] No new tenders to send.")
        return

    # Send email
    if args.dry_run:
        print("\n[Dry Run] Would send email with these tenders:")
        for t in unsent:
            print(f"  - {t[1]}")
    else:
        print("\n[Step 4] Sending email...")
        if send_email(unsent):
            mark_sent([t[0] for t in unsent])
            print(f"[Done] Email sent with {len(unsent)} tenders.")
        else:
            print("[Done] Email not sent (check SMTP settings).")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
