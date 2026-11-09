import mysql.connector
from mysql.connector import errorcode
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from .config import Config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.config = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
            "database": Config.DB_NAME,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
            "autocommit": False,
        }

    @contextmanager
    def connection(self):
        conn = None
        try:
            conn = mysql.connector.connect(**self.config)
            yield conn
            conn.commit()
        except mysql.connector.Error as err:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {err}")
            raise
        finally:
            if conn and conn.is_connected():
                conn.close()

    def get_entity_id(self, short_name: str) -> Optional[int]:
        with self.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM entities WHERE short_name = %s", (short_name,))
            row = cur.fetchone()
            return row["id"] if row else None

    def start_scrape_run(self) -> int:
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO scrape_runs (started_at, status) VALUES (%s, 'running')",
                (datetime.utcnow(),)
            )
            return cur.lastrowid

    def finish_scrape_run(
        self,
        run_id: int,
        entities_scraped: int,
        tenders_found: int,
        tenders_new: int,
        errors: int,
        status: str = "success",
        notes: str = None,
    ):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE scrape_runs
                SET finished_at = %s,
                    entities_scraped = %s,
                    tenders_found = %s,
                    tenders_new = %s,
                    errors = %s,
                    status = %s,
                    notes = %s
                WHERE id = %s
                """,
                (datetime.utcnow(), entities_scraped, tenders_found, tenders_new, errors, status, notes, run_id),
            )

    def upsert_tender(self, entity_id: int, tender: Dict[str, Any]) -> bool:
        """
        Insert or update a tender.
        Returns True if a new tender was inserted, False if updated/existing.
        """
        with self.connection() as conn:
            cur = conn.cursor()

            # Try to find existing by entity + reference (preferred) or entity + title
            existing_id = None
            if tender.get("reference"):
                cur.execute(
                    """
                    SELECT id FROM tenders
                    WHERE entity_id = %s AND reference = %s
                    LIMIT 1
                    """,
                    (entity_id, tender["reference"]),
                )
                row = cur.fetchone()
                if row:
                    existing_id = row[0]

            if not existing_id:
                cur.execute(
                    """
                    SELECT id FROM tenders
                    WHERE entity_id = %s AND title = %s
                    LIMIT 1
                    """,
                    (entity_id, tender["title"][:500]),
                )
                row = cur.fetchone()
                if row:
                    existing_id = row[0]

            now = datetime.utcnow()

            if existing_id:
                cur.execute(
                    """
                    UPDATE tenders
                    SET title = %s,
                        description = COALESCE(%s, description),
                        closing_date = COALESCE(%s, closing_date),
                        closing_time = COALESCE(%s, closing_time),
                        status = %s,
                        document_url = COALESCE(%s, document_url),
                        source_url = %s,
                        last_seen_at = %s,
                        is_active = 1
                    WHERE id = %s
                    """,
                    (
                        tender["title"][:500],
                        tender.get("description"),
                        tender.get("closing_date"),
                        tender.get("closing_time"),
                        tender.get("status", "unknown"),
                        tender.get("document_url"),
                        tender["source_url"],
                        now,
                        existing_id,
                    ),
                )
                return False
            else:
                cur.execute(
                    """
                    INSERT INTO tenders (
                        entity_id, title, reference, description,
                        closing_date, closing_time, status,
                        document_url, source_url, scraped_at, first_seen_at, last_seen_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entity_id,
                        tender["title"][:500],
                        tender.get("reference"),
                        tender.get("description"),
                        tender.get("closing_date"),
                        tender.get("closing_time"),
                        tender.get("status", "unknown"),
                        tender.get("document_url"),
                        tender["source_url"],
                        now,
                        now,
                        now,
                    ),
                )
                return True

    def mark_missing_as_closed(self, entity_id: int, seen_references: List[str]):
        """Mark tenders for this entity that were not seen in the latest scrape as closed (soft)."""
        if not seen_references:
            return
        with self.connection() as conn:
            cur = conn.cursor()
            placeholders = ",".join(["%s"] * len(seen_references))
            cur.execute(
                f"""
                UPDATE tenders
                SET status = 'closed', is_active = 0
                WHERE entity_id = %s
                  AND status = 'open'
                  AND (reference IS NULL OR reference NOT IN ({placeholders}))
                """,
                [entity_id] + seen_references,
            )