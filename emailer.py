"""Build and send the weekly opportunities email.

The email is rendered here (HTML + plain text) rather than in a SendGrid
template, so its design lives in the repo and can be previewed locally:

    python emailer.py --preview            # writes email_preview.html
"""

import argparse
import html
import os
import re
from datetime import datetime

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from config import SENDGRID_API_KEY, EMAIL_FROM, EMAIL_TO, OPPORTUNITY_TYPES
from scrapers.common import matches, parse_date

# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

TENDERS = "Tenders & RFPs"
GRANTS = "Grants & funding"
PROGRAMMES = "Accelerators & competitions"

SECTIONS = [
    (TENDERS, "Contracts you can bid on"),
    (GRANTS, "Grants, funds and calls for proposals"),
    (PROGRAMMES, "Accelerators, incubators, challenges and prizes"),
]

PROGRAMME_TERMS = [
    "accelerator", "acceleration", "incubator", "incubation", "pre-incubation",
    "challenge", "competition", "prize", "pitch", "bootcamp", "fellowship",
]
GRANT_TERMS = [
    "grant", "funding", "fund", "call for proposals", "CFP", "CFA", "investment", "seed funding",
]
# Sources that only publish grant / programme calls
FUNDING_SOURCES = ("fundsforNGOs", "Opportunity Desk", "Opportunities for Africans", "EU Funding")


def categorise(title, source):
    if matches(title, PROGRAMME_TERMS):
        return PROGRAMMES
    if source.startswith(FUNDING_SOURCES) or (matches(title, GRANT_TERMS) and matches(title, OPPORTUNITY_TYPES)):
        return GRANTS
    return TENDERS


# ---------------------------------------------------------------------------
# Tidying
# ---------------------------------------------------------------------------

# Kept upper-case when shouting titles are converted to title case
ACRONYMS = {
    "AI", "API", "CCTV", "CFP", "CFPS", "EOI", "ERP", "EU", "GIS", "ICT", "ID", "IT", "LAN", "MIS",
    "NGO", "NGOS", "PPP", "RFP", "RFQ", "SME", "SMES", "TOR", "UN", "UNDP", "UNICEF", "UPS", "USD",
}
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "via", "with"}
# Scrapers cut long titles at this length
TITLE_LIMIT = 200


def tidy_title(title):
    """Turn ALL-CAPS titles (common on government portals) into title case."""
    title = " ".join((title or "").split())
    if len(title) >= TITLE_LIMIT:
        title = title.rstrip(" ,;:-") + "…"
    letters = [c for c in title if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) / len(letters) < 0.8:
        return title

    def fix(m):
        word, start = m.group(0), m.start()
        # Acronyms, and short codes in brackets like "(CRMS)", stay upper-case
        if word.upper() in ACRONYMS or (len(word) <= 5 and title[start - 1:start] == "("):
            return word
        if word.lower() in SMALL_WORDS and start > 0:
            return word.lower()
        return word.capitalize()

    return re.sub(r"[A-Za-z]+", fix, title)


def tidy_org(org):
    """'UNDP-ZWE/ZIMBABWE' -> 'UNDP Zimbabwe'; other names go through tidy_title."""
    m = re.match(r"UNDP[\w-]*/(.+)", org or "")
    if m:
        return "UNDP " + m.group(1).strip().title()
    return tidy_title(org)


def deadline_info(deadline):
    """Return (sort_key, label, tone) for a deadline string."""
    parsed = parse_date(deadline)
    if not parsed:
        return (datetime.max, "Deadline on listing", "muted")
    days = (parsed.date() - datetime.now().date()).days
    date_text = parsed.strftime("%a %d %b").replace(" 0", " ")
    if days < 0:
        return (parsed, f"Closed {date_text}", "muted")
    if days == 0:
        return (parsed, "Closes today", "urgent")
    if days == 1:
        return (parsed, "Closes tomorrow", "urgent")
    if days <= 7:
        return (parsed, f"Closes in {days} days · {date_text}", "soon")
    return (parsed, f"Closes {date_text}", "normal")


def organise(tenders):
    """Group rows into sections, each sorted by soonest deadline."""
    groups = {name: [] for name, _ in SECTIONS}
    for _id, title, org, deadline, link, source in tenders:
        sort_key, label, tone = deadline_info(deadline)
        source = source or ""
        groups[categorise(title or "", source)].append({
            "title": tidy_title(title),
            "org": tidy_org(org) if org and org != source else "",
            "source": source,
            "link": link,
            "deadline_label": label,
            "tone": tone,
            "sort_key": sort_key,
        })
    for items in groups.values():
        items.sort(key=lambda i: i["sort_key"])
    return groups


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

COLORS = {
    "brand": "#0f3d5e",
    "accent": "#1f8a70",
    "text": "#1d2733",
    "muted": "#5f6b7a",
    "line": "#e3e8ee",
    "page": "#f2f5f8",
    "card": "#ffffff",
}
BADGES = {
    "urgent": ("#fdecea", "#b42318"),
    "soon": ("#fff4e5", "#9a5b00"),
    "normal": ("#eaf4f0", "#1f6b57"),
    "muted": ("#eef1f4", "#5f6b7a"),
}
FONT = "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def _e(text):
    return html.escape(text or "", quote=True)


def _item_html(item):
    bg, fg = BADGES[item["tone"]]
    meta = " · ".join(_e(x) for x in (item["org"], item["source"]) if x)
    return f"""
      <tr><td style="padding:16px 0;border-top:1px solid {COLORS['line']};">
        <a href="{_e(item['link'])}" style="color:{COLORS['text']};text-decoration:none;font-size:16px;line-height:22px;font-weight:600;">{_e(item['title'])}</a>
        <div style="margin-top:4px;font-size:13px;line-height:18px;color:{COLORS['muted']};">{meta}</div>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;width:100%;">
          <tr>
            <td style="font-size:12px;line-height:16px;">
              <span style="display:inline-block;padding:4px 10px;border-radius:12px;background:{bg};color:{fg};font-weight:600;">{_e(item['deadline_label'])}</span>
            </td>
            <td align="right" style="font-size:13px;line-height:16px;white-space:nowrap;">
              <a href="{_e(item['link'])}" style="color:{COLORS['accent']};font-weight:600;text-decoration:none;">View details &rarr;</a>
            </td>
          </tr>
        </table>
      </td></tr>"""


def _section_html(name, blurb, items):
    if not items:
        return ""
    rows = "".join(_item_html(i) for i in items)
    return f"""
  <tr><td style="padding:8px 24px 8px;background:{COLORS['card']};">
    <h2 style="margin:24px 0 2px;font-size:19px;line-height:24px;color:{COLORS['brand']};">{_e(name)} <span style="color:{COLORS['muted']};font-weight:400;">({len(items)})</span></h2>
    <div style="font-size:13px;line-height:18px;color:{COLORS['muted']};margin-bottom:8px;">{_e(blurb)}</div>
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{rows}
    </table>
  </td></tr>"""


def _stat_html(count, label):
    return f"""
          <td align="center" valign="top" style="padding:12px 6px;width:33%;">
            <div style="font-size:26px;line-height:30px;font-weight:700;color:#ffffff;">{count}</div>
            <div style="font-size:12px;line-height:16px;color:#c9d8e4;">{_e(label)}</div>
          </td>"""


def build_email(tenders, today=None):
    """Return (subject, html_body, text_body) for a list of DB rows."""
    today = today or datetime.now()
    groups = organise(tenders)
    total = len(tenders)
    closing_soon = sum(1 for items in groups.values() for i in items if i["tone"] in ("urgent", "soon"))
    date_text = today.strftime("%d %B %Y").lstrip("0")

    parts = [f"{len(groups[name])} {name.split(' &')[0].lower()}" for name, _ in SECTIONS if groups[name]]
    subject = f"{total} new opportunities for Kamagram · {today.strftime('%d %b').lstrip('0')}"
    preheader = ", ".join(parts) + (f" — {closing_soon} closing within a week" if closing_soon else "")

    soon_banner = ""
    if closing_soon:
        soon_banner = f"""
  <tr><td style="padding:14px 24px;background:#fff4e5;color:#7a4700;font-size:14px;line-height:20px;">
    <strong>{closing_soon} closing within a week.</strong> They're at the top of each section.
  </td></tr>"""

    sections = "".join(_section_html(name, blurb, groups[name]) for name, blurb in SECTIONS)
    stats = "".join(_stat_html(len(groups[name]), name) for name, _ in SECTIONS)

    html_body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{_e(subject)}</title>
</head>
<body style="margin:0;padding:0;background:{COLORS['page']};font-family:{FONT};color:{COLORS['text']};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{_e(preheader)}</div>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:{COLORS['page']};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:640px;border-radius:12px;overflow:hidden;background:{COLORS['card']};">

  <tr><td style="padding:28px 24px 8px;background:{COLORS['brand']};">
    <div style="font-size:12px;line-height:16px;letter-spacing:1.5px;text-transform:uppercase;color:#9fc3dc;font-weight:600;">Kamagram Opportunity Radar</div>
    <h1 style="margin:6px 0 4px;font-size:26px;line-height:32px;color:#ffffff;">{total} new opportunities this week</h1>
    <div style="font-size:14px;line-height:20px;color:#c9d8e4;">{_e(date_text)}</div>
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top:16px;border-top:1px solid #2a5878;">
      <tr>{stats}
      </tr>
    </table>
  </td></tr>
{soon_banner}
{sections}
  <tr><td style="padding:24px;background:{COLORS['card']};"></td></tr>
  <tr><td style="padding:20px 24px 28px;background:{COLORS['page']};font-size:12px;line-height:18px;color:{COLORS['muted']};">
    Matched automatically from World Bank, UNDP, EU Funding &amp; Tenders, Kenya PPIP, Uganda eGP, JobInRwanda,
    fundsforNGOs, Opportunity Desk and Opportunities for Africans. Always check eligibility and the full
    terms on the listing before applying.<br><br>
    You'll get this email every Monday when there's something new.
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    lines = [f"KAMAGRAM OPPORTUNITY RADAR — {date_text}", f"{total} new opportunities this week", ""]
    if closing_soon:
        lines += [f"{closing_soon} closing within a week (listed first in each section).", ""]
    for name, _ in SECTIONS:
        if not groups[name]:
            continue
        lines += [f"{name.upper()} ({len(groups[name])})", "-" * 40]
        for i in groups[name]:
            meta = " · ".join(x for x in (i["org"], i["source"]) if x)
            lines += [i["title"], f"  {meta}", f"  {i['deadline_label']}", f"  {i['link']}", ""]
    lines.append("Always check eligibility and the full terms on the listing before applying.")
    text_body = "\n".join(lines)

    return subject, html_body, text_body


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def send_email(tenders):
    """Send the opportunities email through SendGrid."""

    if not SENDGRID_API_KEY:
        print("[Email] SENDGRID_API_KEY not set. Skipping email send.")
        print("[Email] Set the SENDGRID_API_KEY environment variable to enable emails.")
        return False

    subject, html_body, text_body = build_email(tenders)
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=EMAIL_TO,
        subject=subject,
        html_content=html_body,
        plain_text_content=text_body,
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[Email] Successfully sent to {', '.join(EMAIL_TO)} (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"[Email] Failed to send: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview or test the opportunities email")
    parser.add_argument("--preview", nargs="?", const="email_preview.html", metavar="FILE",
                        help="Write the email built from the database to an HTML file instead of sending")
    args = parser.parse_args()

    if args.preview:
        from db import init_db, get_all_tenders
        init_db()
        rows = [r[:6] for r in get_all_tenders()]
        subject, html_body, text_body = build_email(rows)
        with open(args.preview, "w", encoding="utf-8") as f:
            f.write(html_body)
        with open(os.path.splitext(args.preview)[0] + ".txt", "w", encoding="utf-8") as f:
            f.write(f"Subject: {subject}\n\n{text_body}")
        print(f"Subject: {subject}")
        print(f"Wrote {args.preview} ({len(rows)} opportunities from the database)")
    else:
        # Send a test email with dummy data
        send_email([
            (1, "Website Development for Ministry", "Ministry of ICT", "15 Feb 2026", "https://example.com/tender1", "TestSource"),
            (2, "Mobile App Development", "Rwanda Revenue Authority", "20 Feb 2026", "https://example.com/tender2", "TestSource"),
        ])
