import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime
from config import SENDGRID_API_KEY, SENDGRID_TEMPLATE_ID, EMAIL_FROM, EMAIL_TO


def send_email(tenders):
    """Send email with tender opportunities using SendGrid dynamic template."""

    if not SENDGRID_API_KEY:
        print("[Email] SENDGRID_API_KEY not set. Skipping email send.")
        print("[Email] Set the SENDGRID_API_KEY environment variable to enable emails.")
        return False

    if not SENDGRID_TEMPLATE_ID:
        print("[Email] SENDGRID_TEMPLATE_ID not set. Skipping email send.")
        return False

    today_short = datetime.now().strftime("%d %b %Y")
    today_full = datetime.now().strftime("%d %B, %Y").lstrip("0")  # e.g., "5 February, 2026"

    # Build items array for SendGrid dynamic template
    # Template expects: {{#each items}} with {{org}}, {{company}}, {{details}}, {{deadline}}, {{link}}
    items = []
    for t in tenders:
        # t is a tuple: (id, title, organization, deadline, link, source)
        items.append({
            "org": t[2] or "Unknown Organization",
            "company": t[5],  # source (e.g., "JobInRwanda")
            "details": t[1],  # title
            "deadline": t[3] or "Not specified",
            "link": t[4],
        })

    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=EMAIL_TO,
    )

    message.template_id = SENDGRID_TEMPLATE_ID
    message.dynamic_template_data = {
        "subject": f"Kamagram Tender Radar - {len(tenders)} New Opportunities ({today_short})",
        "items": items,
        "count": len(tenders),
        "date": today_full,
    }

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[Email] Successfully sent to {EMAIL_TO} (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"[Email] Failed to send: {e}")
        return False


if __name__ == "__main__":
    # Test with dummy data
    test_tenders = [
        (1, "Website Development for Ministry", "Ministry of ICT", "15 Feb 2026", "https://example.com/tender1", "TestSource"),
        (2, "Mobile App Development", "Rwanda Revenue Authority", "20 Feb 2026", "https://example.com/tender2", "TestSource"),
    ]
    send_email(test_tenders)
