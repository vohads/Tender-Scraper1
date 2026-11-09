import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "tender_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "namibia_tenders")

    SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", 30))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (compatible; NamibiaTenderBot/1.0; +https://github.com/yourusername/namibia-tender-scraper)"
    )
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

    # Entities to scrape (short_name -> optional override tender URL)
    ENTITIES = {
        "Agribank": "https://agribank.com.na/page/bidders",
        "DBN": "https://www.dbn.com.na/invitation-of-bids-clarifications/",
        "NHE": "https://www.nhe.com.na/open-bids/",
        "MTC": "https://www.mtc.com.na/procurement/tenders",
        # Others currently have weak/no public tender listings – still checked via homepage + common paths
        "EIF": "https://www.eifnamibia.com/",
        "GPTF": "https://www.gptf.org.na/",
        "NamibRe": "https://namibre.com/",
        "RFA": "https://www.rfanam.com.na/",
        "SSC": "https://www.ssc.org.na/",
        "Epangelo": "https://www.epangelomining.na/",
        "Meatco": "https://www.meatco.com.na/",
        "NAC": "https://www.airports.com.na/",
        "Namdia": "https://namdia.na/",
        "NIDA": "https://www.nida.com.na/",
        "NamPost": "https://www.nampost.com.na/",
    }