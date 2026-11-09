# Namibia Public Enterprises Tender Scraper

Scrapes active / open tenders from major Namibian public enterprises and stores them in a MySQL database.

Designed to run easily in **GitHub Codespaces** (or any Linux environment) and scheduled via cron or GitHub Actions.

## Supported Entities

| Short name | Organisation                          | Dedicated tender page |
|------------|---------------------------------------|-----------------------|
| Agribank   | Agricultural Bank of Namibia          | Yes                   |
| DBN        | Development Bank of Namibia           | Yes                   |
| NHE        | National Housing Enterprise           | Yes                   |
| MTC        | Mobile Telecommunications Limited     | Yes                   |
| EIF, GPTF, NamibRe, RFA, SSC, Epangelo, Meatco, NAC, Namdia, NIDA, NamPost | Various | Generic fallback      |

## Quick Start (GitHub Codespaces)

### 1. Create the Codespace
- Push this repo to GitHub
- Click **Code → Codespaces → Create codespace on main**

### 2. Start MySQL in the Codespace

```bash
# Install MySQL server (one-time)
sudo apt-get update
sudo apt-get install -y mysql-server

# Start it
sudo service mysql start

# Secure & create user/db (example)
sudo mysql -e "CREATE DATABASE IF NOT EXISTS namibia_tenders CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'tender_user'@'localhost' IDENTIFIED BY 'change_me_strong_password';"
sudo mysql -e "GRANT ALL PRIVILEGES ON namibia_tenders.* TO 'tender_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
```

### 3. Load the schema

```bash
mysql -u tender_user -p namibia_tenders < sql/schema.sql
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your real DB password etc.
nano .env
```

### 5. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6. Run once (dry-run first)

```bash
# Dry run – no DB writes
DRY_RUN=true python -m scraper.main

# Real run
python -m scraper.main
```

## Running as a Cron Job

Inside the Codespace (or any Linux host):

```bash
# Edit crontab
crontab -e
```

Add a line (example: every day at 06:30 and 14:30 CAT):

```cron
30 6,14 * * * cd /workspaces/namibia-tender-scraper && /workspaces/namibia-tender-scraper/.venv/bin/python -m scraper.main >> /tmp/tender-scraper.log 2>&1
```

Or use a systemd timer / GitHub Actions scheduled workflow for more reliability.

## Project Structure

```
namibia-tender-scraper/
├── scraper/
│   ├── __init__.py
│   ├── config.py          # Settings from .env
│   ├── db.py              # MySQL helpers
│   ├── base.py            # Base scraper + helpers
│   ├── scrapers.py        # Entity-specific scrapers
│   └── main.py            # Entry point
├── sql/
│   └── schema.sql         # Database schema + seed data
├── .env.example
├── requirements.txt
└── README.md
```

## Extending

To add a better scraper for another entity:

1. Create a new class inheriting from `BaseScraper` in `scrapers.py`
2. Implement the `scrape()` method
3. Add it to `get_all_scrapers()`

## Notes & Limitations

- Many Namibian PE websites do not publish a clean, structured open-tenders list. Some only post PDFs or annual procurement plans.
- Closing dates are best-effort parsed from free text.
- The scraper is polite (retries with backoff, rotates user-agent).
- For production you may want to add Playwright for heavy JavaScript sites later.
- Always respect the sites’ terms of use and robots.txt.

## License

MIT – use freely, attribution appreciated.
