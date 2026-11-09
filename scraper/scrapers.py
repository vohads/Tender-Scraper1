import re
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin

from .base import BaseScraper

logger = logging.getLogger(__name__)


class AgribankScraper(BaseScraper):
    short_name = "Agribank"
    base_url = "https://www.agribank.com.na/"
    tender_url = "https://agribank.com.na/page/bidders"

    def scrape(self) -> List[Dict[str, Any]]:
        soup = self.fetch(self.tender_url)
        if not soup:
            return []

        tenders = []
        # The page is simple – look for date + title patterns
        content = soup.get_text("\n", strip=True)

        # Look for PDF links or titled sections
        for a in soup.select("a[href*='.pdf'], a[href*='download']"):
            title = self.clean_text(a.get_text() or a.get("title") or "")
            href = a.get("href", "")
            if not title or len(title) < 10:
                continue
            if any(x in title.lower() for x in ["request", "quotation", "tender", "bid", "rfq", "rfp", "procurement"]):
                doc_url = urljoin(self.base_url, href)
                tenders.append({
                    "title": title[:500],
                    "reference": None,
                    "description": None,
                    "closing_date": self.parse_date(title) or self.parse_date(content),
                    "closing_time": None,
                    "status": "open",
                    "document_url": doc_url,
                    "source_url": self.tender_url,
                })

        # Fallback: page-level title if present
        if not tenders:
            h = soup.find(["h1", "h2", "h3"])
            if h and "bid" in h.get_text().lower():
                tenders.append({
                    "title": self.clean_text(h.get_text()),
                    "reference": None,
                    "description": None,
                    "closing_date": None,
                    "closing_time": None,
                    "status": "open",
                    "document_url": None,
                    "source_url": self.tender_url,
                })

        return tenders


class DBNScraper(BaseScraper):
    short_name = "DBN"
    base_url = "https://www.dbn.com.na/"
    tender_url = "https://www.dbn.com.na/invitation-of-bids-clarifications/"

    def scrape(self) -> List[Dict[str, Any]]:
        soup = self.fetch(self.tender_url)
        if not soup:
            return []

        tenders = []
        # DBN lists items as bold titles followed by Closing Date lines
        text = soup.get_text("\n", strip=True)
        blocks = re.split(r"\n(?=\*\*|Procurement of|Provision )", text)

        for block in blocks:
            block = block.strip()
            if len(block) < 20:
                continue
            if not any(k in block.lower() for k in ["procurement", "provision", "closing date", "rfq", "rfp"]):
                continue

            lines = [l.strip() for l in block.split("\n") if l.strip()]
            title = lines[0].lstrip("* ").strip()
            closing_date = None
            closing_time = None

            for line in lines:
                if "closing date" in line.lower():
                    closing_date = self.parse_date(line)
                if "closing time" in line.lower() or re.search(r"\d{1,2}h\d{2}", line, re.I):
                    m = re.search(r"(\d{1,2}h\d{2}|\d{1,2}:\d{2})", line, re.I)
                    if m:
                        closing_time = m.group(1)

            if title and len(title) > 15:
                status = "open"
                # crude past-date check could be added later
                tenders.append({
                    "title": title[:500],
                    "reference": None,
                    "description": None,
                    "closing_date": closing_date,
                    "closing_time": closing_time,
                    "status": status,
                    "document_url": None,
                    "source_url": self.tender_url,
                })

        return tenders


class NHEScraper(BaseScraper):
    short_name = "NHE"
    base_url = "https://www.nhe.com.na/"
    tender_url = "https://www.nhe.com.na/open-bids/"

    def scrape(self) -> List[Dict[str, Any]]:
        soup = self.fetch(self.tender_url)
        if not soup:
            return []

        tenders = []
        table = soup.find("table")
        if not table:
            return []

        rows = table.find_all("tr")
        headers = [self.clean_text(th.get_text()) for th in rows[0].find_all(["th", "td"])] if rows else []

        for row in rows[1:]:
            cols = [self.clean_text(td.get_text()) for td in row.find_all("td")]
            if len(cols) < 3:
                continue

            # Expected columns roughly: Description | Reference | Closing Date | ... | Status
            title = cols[0]
            reference = cols[1] if len(cols) > 1 else None
            closing_raw = cols[2] if len(cols) > 2 else ""
            status_raw = cols[5].lower() if len(cols) > 5 else "unknown"

            if status_raw not in ("open",):
                # Only keep currently open ones for the main feed
                continue

            closing_date = self.parse_date(closing_raw)
            closing_time = None
            m = re.search(r"(\d{1,2}[hH:]\d{2})", closing_raw)
            if m:
                closing_time = m.group(1)

            # Try to find download link
            doc_url = None
            a = row.find("a", href=True)
            if a:
                doc_url = urljoin(self.base_url, a["href"])

            tenders.append({
                "title": title[:500],
                "reference": reference,
                "description": None,
                "closing_date": closing_date,
                "closing_time": closing_time,
                "status": "open",
                "document_url": doc_url,
                "source_url": self.tender_url,
            })

        return tenders


class MTCScraper(BaseScraper):
    short_name = "MTC"
    base_url = "https://www.mtc.com.na/"
    tender_url = "https://www.mtc.com.na/procurement/tenders"

    def scrape(self) -> List[Dict[str, Any]]:
        soup = self.fetch(self.tender_url)
        if not soup:
            return []

        tenders = []
        # MTC shows cards / list with title + closing date + status
        for item in soup.select("div, article, li, a"):
            text = self.clean_text(item.get_text())
            if not text or len(text) < 20:
                continue
            if "REQUEST FOR" not in text.upper() and "MTC" not in text.upper():
                continue

            # Look for tender codes like MTC53-26-O
            ref_match = re.search(r"(MTC\d{2,}-\d{2}-[A-Z]+)", text, re.I)
            reference = ref_match.group(1) if ref_match else None

            title = text.split("Closing")[0].strip()[:500]
            if len(title) < 15:
                continue

            closing_date = self.parse_date(text)
            status = "open"
            if "closed" in text.lower():
                status = "closed"
            elif "evaluation" in text.lower():
                status = "under_evaluation"

            # Prefer only open ones
            if status != "open":
                continue

            href = item.get("href") if item.name == "a" else None
            source = urljoin(self.base_url, href) if href else self.tender_url

            tenders.append({
                "title": title,
                "reference": reference,
                "description": None,
                "closing_date": closing_date,
                "closing_time": None,
                "status": status,
                "document_url": None,
                "source_url": source,
            })

        # Deduplicate by reference/title
        seen = set()
        unique = []
        for t in tenders:
            key = (t.get("reference") or "") + t["title"][:80]
            if key not in seen:
                seen.add(key)
                unique.append(t)

        return unique


class GenericScraper(BaseScraper):
    """Fallback for sites without a clear dedicated tender page."""

    def __init__(self, short_name: str, base_url: str, tender_url: str = None):
        super().__init__()
        self.short_name = short_name
        self.base_url = base_url
        self.tender_url = tender_url or base_url

    def scrape(self) -> List[Dict[str, Any]]:
        # Try common tender paths
        candidates = [
            self.tender_url,
            urljoin(self.base_url, "/tenders"),
            urljoin(self.base_url, "/procurement"),
            urljoin(self.base_url, "/tenders-and-procurement"),
            urljoin(self.base_url, "/open-bids"),
            urljoin(self.base_url, "/procurement/tenders"),
        ]

        tenders = []
        for url in candidates:
            try:
                soup = self.fetch(url)
                if not soup:
                    continue

                # Look for obvious tender links
                for a in soup.select("a[href]"):
                    text = self.clean_text(a.get_text())
                    href = a.get("href", "")
                    if not text or len(text) < 15:
                        continue
                    lower = text.lower()
                    if any(k in lower for k in ["tender", "rfq", "rfp", "request for", "bid", "quotation", "procurement"]):
                        tenders.append({
                            "title": text[:500],
                            "reference": None,
                            "description": None,
                            "closing_date": self.parse_date(text),
                            "closing_time": None,
                            "status": "open",
                            "document_url": urljoin(self.base_url, href) if href.endswith(".pdf") else None,
                            "source_url": url,
                        })
                if tenders:
                    break
            except Exception as e:
                logger.debug(f"[{self.short_name}] {url} failed: {e}")
                continue

        return tenders


def get_all_scrapers() -> List[BaseScraper]:
    """Return the list of scrapers to run."""
    scrapers = [
        AgribankScraper(),
        DBNScraper(),
        NHEScraper(),
        MTCScraper(),
    ]

    # Generic ones for the rest
    generics = {
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
    for short, url in generics.items():
        scrapers.append(GenericScraper(short, url))

    return scrapers