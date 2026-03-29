"""
Project SVARNA — Blackboard State Manager
==========================================
Shared state for inter-agent communication.
Uses SQLite for persistence + in-memory dict for fast access.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class Blackboard:
    """
    Blackboard Architecture — shared state store for all agents.
    
    - SQLite backend for persistence and audit trail
    - In-memory cache for fast reads
    - Thread-safe access
    """

    def __init__(self, db_path: str = "data/svarna_blackboard.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._memory: dict[str, list[dict]] = {
            "transcriptions": [],
            "parsed_reports": [],
            "economic_alerts": [],
            "audit_log": [],
        }
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blackboard (
                    id TEXT PRIMARY KEY,
                    agent_source TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
        logger.info(f"Blackboard initialized at {self.db_path}")

    # -----------------------------------------------------------------
    # Write
    # -----------------------------------------------------------------

    def write(
        self,
        entry_id: str,
        agent_source: str,
        entry_type: str,
        payload: dict,
    ) -> None:
        """Write an entry to the blackboard (both DB and memory)."""
        with self._lock:
            timestamp = datetime.now().isoformat()
            record = {
                "id": entry_id,
                "agent_source": agent_source,
                "entry_type": entry_type,
                "payload": payload,
                "created_at": timestamp,
            }

            # Memory
            if entry_type not in self._memory:
                self._memory[entry_type] = []
            self._memory[entry_type].append(record)

            # SQLite
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO blackboard 
                           (id, agent_source, entry_type, payload, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (entry_id, agent_source, entry_type,
                         json.dumps(payload, default=str), timestamp),
                    )
                    conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Blackboard SQLite write error: {e}")

            self._audit(agent_source, "WRITE", f"{entry_type}:{entry_id}")
            logger.debug(f"[Blackboard] {agent_source} wrote {entry_type}:{entry_id}")

    # -----------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------

    def read(
        self,
        entry_type: str,
        limit: int = 50,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        """Read entries from memory cache by type."""
        with self._lock:
            entries = self._memory.get(entry_type, [])
            if status_filter:
                entries = [
                    e for e in entries
                    if e.get("payload", {}).get("status") == status_filter
                ]
            return entries[-limit:]

    def read_by_id(self, entry_id: str) -> Optional[dict]:
        """Retrieve a specific entry by ID."""
        with self._lock:
            for entries in self._memory.values():
                for entry in entries:
                    if entry["id"] == entry_id:
                        return entry
        return None

    def read_latest(self, entry_type: str) -> Optional[dict]:
        """Get the most recent entry of a given type."""
        entries = self.read(entry_type, limit=1)
        return entries[-1] if entries else None

    # -----------------------------------------------------------------
    # Query (from SQLite for historical data)
    # -----------------------------------------------------------------

    def query_history(
        self,
        entry_type: str,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query historical entries from SQLite."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                if since:
                    rows = conn.execute(
                        """SELECT * FROM blackboard 
                           WHERE entry_type = ? AND created_at >= ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (entry_type, since, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT * FROM blackboard 
                           WHERE entry_type = ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (entry_type, limit),
                    ).fetchall()
                return [
                    {**dict(row), "payload": json.loads(row["payload"])}
                    for row in rows
                ]
        except sqlite3.Error as e:
            logger.error(f"Blackboard query error: {e}")
            return []

    # -----------------------------------------------------------------
    # Stats
    # -----------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Return count of entries by type."""
        with self._lock:
            return {k: len(v) for k, v in self._memory.items()}

    # -----------------------------------------------------------------
    # Audit
    # -----------------------------------------------------------------

    def _audit(self, agent: str, action: str, details: str) -> None:
        """Record an action in the audit log."""
        timestamp = datetime.now().isoformat()
        self._memory["audit_log"].append({
            "agent": agent,
            "action": action,
            "details": details,
            "timestamp": timestamp,
        })
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """INSERT INTO audit_log (agent, action, details, timestamp)
                       VALUES (?, ?, ?, ?)""",
                    (agent, action, details, timestamp),
                )
                conn.commit()
        except sqlite3.Error:
            pass  # Non-critical

    def clear_memory(self) -> None:
        """Clear in-memory cache (keeps SQLite data)."""
        with self._lock:
            for key in self._memory:
                self._memory[key] = []
            logger.info("Blackboard memory cache cleared")
