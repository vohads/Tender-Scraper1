import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fake_useragent import UserAgent

from .config import Config

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    short_name: str = "Base"
    base_url: str = ""
    tender_url: Optional[str] = None

    def __init__(self):
        self.session = requests.Session()
        try:
            ua = UserAgent()
            user_agent = ua.random
        except Exception:
            user_agent = Config.USER_AGENT

        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        self.timeout = Config.SCRAPE_TIMEOUT

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        logger.info(f"[{self.short_name}] Fetching {url}")
        resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, "lxml")

    def parse_date(self, text: str) -> Optional[str]:
        """Try to extract a YYYY-MM-DD date from free text."""
        if not text:
            return None
        text = text.strip()

        # Common formats
        patterns = [
            r"(\d{4}-\d{2}-\d{2})",                          # 2026-11-20
            r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
            r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})",          # 20/11/2026 or 20-11-2026
            r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})",
        ]

        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }

        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                groups = m.groups()
                try:
                    if len(groups) == 1 and "-" in groups[0]:
                        return groups[0]
                    if len(groups) == 3:
                        if groups[1].isalpha():
                            day = int(groups[0])
                            month = months[groups[1].lower()[:3]]
                            year = int(groups[2])
                            return f"{year:04d}-{month:02d}-{day:02d}"
                        else:
                            # assume DD/MM/YYYY (Namibia style)
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                            return f"{year:04d}-{month:02d}-{day:02d}"
                except Exception:
                    continue
        return None

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """Return list of tender dicts."""
        pass

    def run(self) -> List[Dict[str, Any]]:
        try:
            tenders = self.scrape()
            logger.info(f"[{self.short_name}] Found {len(tenders)} tender(s)")
            return tenders
        except Exception as e:
            logger.error(f"[{self.short_name}] Scrape failed: {e}", exc_info=True)
            return []