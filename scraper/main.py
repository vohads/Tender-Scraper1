#!/usr/bin/env python3
"""
Namibia Public Enterprises Tender Scraper
Run once or via cron / GitHub Actions / Codespaces scheduled task.
"""

import logging
import sys
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .config import Config
from .db import Database
from .scrapers import get_all_scrapers

console = Console()


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def run():
    setup_logging()
    logger = logging.getLogger("scraper")

    console.rule("[bold blue]Namibia PE Tender Scraper")
    console.print(f"Started at {datetime.utcnow().isoformat()}Z")
    console.print(f"Dry-run mode: {Config.DRY_RUN}")

    db = Database()
    run_id = None
    entities_scraped = 0
    tenders_found = 0
    tenders_new = 0
    errors = 0

    try:
        if not Config.DRY_RUN:
            run_id = db.start_scrape_run()
            logger.info(f"Scrape run ID: {run_id}")

        scrapers = get_all_scrapers()
        results_table = Table(title="Scrape Results")
        results_table.add_column("Entity", style="cyan")
        results_table.add_column("Found", justify="right")
        results_table.add_column("New", justify="right")
        results_table.add_column("Status")

        for scraper in scrapers:
            entity_name = scraper.short_name
            try:
                tenders = scraper.run()
                entities_scraped += 1
                found = len(tenders)
                tenders_found += found
                new_count = 0

                if not Config.DRY_RUN and tenders:
                    entity_id = db.get_entity_id(entity_name)
                    if not entity_id:
                        logger.warning(f"Entity '{entity_name}' not found in DB – skipping insert")
                    else:
                        seen_refs = []
                        for t in tenders:
                            is_new = db.upsert_tender(entity_id, t)
                            if is_new:
                                new_count += 1
                            if t.get("reference"):
                                seen_refs.append(t["reference"])
                        tenders_new += new_count
                        # Optional: mark missing open tenders as closed
                        # db.mark_missing_as_closed(entity_id, seen_refs)

                status = "OK" if found >= 0 else "EMPTY"
                results_table.add_row(entity_name, str(found), str(new_count), status)

            except Exception as e:
                errors += 1
                logger.error(f"Failed on {entity_name}: {e}")
                results_table.add_row(entity_name, "0", "0", f"[red]ERROR[/red]")

        console.print(results_table)

        final_status = "success"
        if errors and entities_scraped:
            final_status = "partial"
        elif errors and not entities_scraped:
            final_status = "failed"

        if not Config.DRY_RUN and run_id:
            db.finish_scrape_run(
                run_id,
                entities_scraped=entities_scraped,
                tenders_found=tenders_found,
                tenders_new=tenders_new,
                errors=errors,
                status=final_status,
            )

        console.print(f"\n[bold green]Done.[/bold green] "
                      f"Entities: {entities_scraped} | "
                      f"Tenders found: {tenders_found} | "
                      f"New: {tenders_new} | "
                      f"Errors: {errors}")

        return 0 if final_status != "failed" else 1

    except Exception as e:
        logger.exception("Fatal error")
        if run_id and not Config.DRY_RUN:
            try:
                db.finish_scrape_run(run_id, entities_scraped, tenders_found, tenders_new, errors + 1, "failed", str(e))
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    sys.exit(run())