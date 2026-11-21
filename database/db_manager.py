"""database/db_manager.py

SQLite connection lifecycle, schema initialization, and atomic transaction
management for Setuvo. Ensures foreign-key integrity and safe concurrent
stock checking/reduction during checkout.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any, Generator, Iterable, List, Optional, Union

from config import Config


class DatabaseManager:
    """Manages SQLite connections, schema creation, and atomic transactions."""

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        schema_path: Optional[Union[str, Path]] = None,
    ) -> None:
        raw_db = db_path if db_path is not None else Config.DATABASE_PATH
        self.is_memory: bool = str(raw_db) == ":memory:"
        self.db_path: Union[str, Path] = ":memory:" if self.is_memory else Path(raw_db)
        self.schema_path: Path = Path(schema_path or Config.SCHEMA_PATH)
        self._memory_conn: Optional[sqlite3.Connection] = None

        if not self.is_memory:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        """Creates a configured SQLite connection with foreign keys enabled."""
        target = ":memory:" if self.is_memory else str(self.db_path)
        conn = sqlite3.connect(
            target,
            timeout=10.0,
            isolation_level=None,  # Explicit transaction control via BEGIN/COMMIT/ROLLBACK
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        if not self.is_memory:
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _acquire_connection(self) -> tuple[sqlite3.Connection, bool]:
        """Returns (connection, should_close_after_use)."""
        if self.is_memory:
            if self._memory_conn is None:
                self._memory_conn = self._create_connection()
            return self._memory_conn, False
        return self._create_connection(), True

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Yields a configured SQLite connection for read or auto-committed operations."""
        conn, should_close = self._acquire_connection()
        try:
            yield conn
        finally:
            if should_close:
                conn.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Executes operations inside an atomic BEGIN IMMEDIATE SQLite transaction.

        Prevents two simultaneous checkouts from overselling the final units
        of stock by acquiring a write lock before stock checks and updates run.
        """
        conn, should_close = self._acquire_connection()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            yield conn
            conn.execute("COMMIT;")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK;")
            raise
        finally:
            if should_close:
                conn.close()

    def init_db(self) -> None:
        """Executes schema.sql to create all tables and indexes if absent."""
        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"Database schema file not found at: {self.schema_path}"
            )

        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(schema_sql)
            conn.execute("PRAGMA foreign_keys = ON;")

    def fetch_one(
        self, sql: str, params: Iterable[Any] = ()
    ) -> Optional[sqlite3.Row]:
        """Executes a SELECT query and returns a single Row or None."""
        with self.connect() as conn:
            cursor = conn.execute(sql, tuple(params))
            return cursor.fetchone()

    def fetch_all(
        self, sql: str, params: Iterable[Any] = ()
    ) -> List[sqlite3.Row]:
        """Executes a SELECT query and returns all matching Rows."""
        with self.connect() as conn:
            cursor = conn.execute(sql, tuple(params))
            return list(cursor.fetchall())

    def get_table_names(self) -> List[str]:
        """Returns sorted user-defined table names in the SQLite database."""
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name ASC;"
        )
        return [str(row["name"]) for row in rows]

    def close(self) -> None:
        """Closes the persistent in-memory connection if active."""
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None