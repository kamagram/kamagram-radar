import os

from dotenv import load_dotenv

# Load variables from .env next to this file (no-op if it doesn't exist).
# Real environment variables, e.g. GitHub Actions secrets, take precedence.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Countries Kamagram bids in (used by sources that can filter by country)
TARGET_COUNTRIES = ["Rwanda", "Kenya", "Uganda", "Tanzania", "South Africa"]

# Kamagram's line of work - used to filter RFPs and tenders.
# Matched as whole words (plurals allowed), case-insensitive.
KEYWORDS = [
    # Web & Mobile
    "website",
    "web portal",
    "web application",
    "web app",
    "web platform",
    "mobile app",
    "mobile application",
    "app development",
    # Software & systems
    "software",
    "information system",
    "management system",
    "ERP",
    "database",
    # Not plain "ICT": it mostly matches hardware, furniture and CCTV supply tenders
    "ICT consultancy",
    "ICT services",
    "ICT solutions",
    "ICT system",
    "IT consultancy",
    "IT services",
    "system development",
    "systems development",
    # Digital
    "digital platform",
    "digital transformation",
    "digitalization",
    "digitalisation",
    "digitization",
    "digitisation",
    "e-commerce",
    "e-government",
    "e-learning",
    "online platform",
    "artificial intelligence",
    "machine learning",
]

# Kinds of opportunity we want from grant / accelerator / funding feeds
OPPORTUNITY_TYPES = [
    "grant",
    "funding",
    "fund",
    "call for proposals",
    "call for applications",
    "request for proposals",
    "accelerator",
    "acceleration",
    "incubator",
    "incubation",
    "startup programme",
    "startup program",
    "challenge",
    "competition",
    "prize",
    "pitch",
    "investment",
    "investor",
    "venture",
    "seed funding",
]

# Topics that make a grant / accelerator / funding call relevant to a software company
FUNDING_TOPICS = KEYWORDS + [
    "tech",
    "technology",
    "digital",
    "innovation",
    "innovator",
    "startup",
    "start-up",
    "fintech",
    "edtech",
    "agritech",
    "healthtech",
    "AI",
    "ICT",
]

# A grant / accelerator call must mention one of these to be open to Kamagram
REGIONS = TARGET_COUNTRIES + [
    "Africa",
    "African",
    "East Africa",
    "sub-Saharan",
    "global",
    "worldwide",
    "international",
    "developing countries",
    "all countries",
    "LMIC",
]

# SendGrid settings - use environment variables for security
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDGRID_TEMPLATE_ID = os.environ.get("SENDGRID_TEMPLATE_ID", "d-11064e123cf445bcab85f0d5fd2c4ec9")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "alerts@kamagram.com")
# Comma-separated list of recipients
EMAIL_TO = [
    addr.strip()
    for addr in os.environ.get("EMAIL_TO", "marvin@kamagram.com,lisa@kamagram.com").split(",")
    if addr.strip()
]

# Sources to enable/disable
SOURCES = {
    # RFPs & tenders
    "jobinrwanda": True,  # Rwanda tenders & consultancies
    "worldbank": True,  # World Bank procurement notices in TARGET_COUNTRIES
    "kenya_ppip": True,  # Kenya Public Procurement Information Portal
    "uganda_egp": True,  # Uganda Electronic Government Procurement
    "undp": True,  # UNDP procurement notices, Africa region
    # Grants, accelerators & funding calls
    "eu_funding": True,  # EU Funding & Tenders portal, Africa-related calls
    "opportunity_feeds": True,  # fundsforNGOs, Opportunity Desk, Opportunities for Africans
    # Disabled
    "devex": False,  # Requires JavaScript rendering - use google_search instead
    "tenderafrica": False,  # Site currently returning 404
    "reliefweb": False,  # Requires RELIEFWEB_APPNAME (register at apidoc.reliefweb.int)
    "google_search": False,  # Requires Google Cloud billing
}

# Google Custom Search settings (optional)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")
