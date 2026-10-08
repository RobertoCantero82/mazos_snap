import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple

try:
    from .models import DeckSnapshot
except ImportError:
    from models import DeckSnapshot


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(MODULE_DIR) if os.path.basename(MODULE_DIR) == "src" else MODULE_DIR
DB_PATH = os.path.join(BASE_DIR, "data", "mazos_snap.db")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with closing(connect()) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL UNIQUE,
                external_id TEXT,
                name TEXT NOT NULL,
                archetype TEXT NOT NULL,
                cards_json TEXT NOT NULL,
                deck_code TEXT NOT NULL,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_period TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                times_seen INTEGER NOT NULL DEFAULT 1,
                players INTEGER NOT NULL DEFAULT 0,
                qualified_players INTEGER NOT NULL DEFAULT 0,
                matches INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                win_rate REAL NOT NULL DEFAULT 0,
                cube_rate REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS deck_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                observed_at TEXT NOT NULL,
                players INTEGER NOT NULL,
                matches INTEGER NOT NULL,
                wins INTEGER NOT NULL,
                losses INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                cube_rate REAL NOT NULL,
                source_period TEXT NOT NULL,
                FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                fetched_count INTEGER NOT NULL DEFAULT 0,
                inserted_count INTEGER NOT NULL DEFAULT 0,
                updated_count INTEGER NOT NULL DEFAULT 0,
                message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_decks_first_seen ON decks(first_seen DESC);
            CREATE INDEX IF NOT EXISTS idx_decks_archetype ON decks(archetype);
            CREATE INDEX IF NOT EXISTS idx_observations_deck ON deck_observations(deck_id, observed_at DESC);
            """
        )


def start_run() -> int:
    now = utc_now()
    with closing(connect()) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO runs(started_at, status) VALUES (?, 'running')", (now,)
        )
        return int(cursor.lastrowid)


def finish_run(
    run_id: int,
    *,
    status: str,
    fetched: int = 0,
    inserted: int = 0,
    updated: int = 0,
    message: str = "",
) -> None:
    with closing(connect()) as conn, conn:
        conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, status = ?, fetched_count = ?, inserted_count = ?,
                updated_count = ?, message = ?
            WHERE id = ?
            """,
            (utc_now(), status, fetched, inserted, updated, message[:2000], run_id),
        )


def upsert_decks(decks: Iterable[DeckSnapshot], observed_at: str | None = None) -> Tuple[int, int]:
    observed_at = observed_at or utc_now()
    inserted = 0
    updated = 0
    with closing(connect()) as conn, conn:
        for deck in decks:
            existing = conn.execute(
                "SELECT id FROM decks WHERE fingerprint = ?", (deck.fingerprint,)
            ).fetchone()
            if existing:
                deck_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE decks SET
                        external_id = ?, name = ?, archetype = ?, cards_json = ?,
                        deck_code = ?, source = ?, source_url = ?, source_period = ?,
                        last_seen = ?, times_seen = times_seen + 1, players = ?,
                        qualified_players = ?, matches = ?, wins = ?, losses = ?,
                        win_rate = ?, cube_rate = ?, active = 1
                    WHERE id = ?
                    """,
                    _deck_values(deck, observed_at) + (deck_id,),
                )
                updated += 1
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO decks (
                        fingerprint, external_id, name, archetype, cards_json,
                        deck_code, source, source_url, source_period, first_seen,
                        last_seen, players, qualified_players, matches, wins, losses,
                        win_rate, cube_rate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        deck.fingerprint,
                        deck.external_id,
                        deck.name,
                        deck.archetype,
                        json.dumps(deck.cards, ensure_ascii=False),
                        deck.deck_code,
                        deck.source,
                        deck.source_url,
                        deck.source_period,
                        observed_at,
                        observed_at,
                        deck.players,
                        deck.qualified_players,
                        deck.matches,
                        deck.wins,
                        deck.losses,
                        deck.win_rate,
                        deck.cube_rate,
                    ),
                )
                deck_id = int(cursor.lastrowid)
                inserted += 1
            conn.execute(
                """
                INSERT INTO deck_observations (
                    deck_id, observed_at, players, matches, wins, losses,
                    win_rate, cube_rate, source_period
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deck_id,
                    observed_at,
                    deck.players,
                    deck.matches,
                    deck.wins,
                    deck.losses,
                    deck.win_rate,
                    deck.cube_rate,
                    deck.source_period,
                ),
            )
    return inserted, updated


def _deck_values(deck: DeckSnapshot, observed_at: str) -> tuple:
    return (
        deck.external_id,
        deck.name,
        deck.archetype,
        json.dumps(deck.cards, ensure_ascii=False),
        deck.deck_code,
        deck.source,
        deck.source_url,
        deck.source_period,
        observed_at,
        deck.players,
        deck.qualified_players,
        deck.matches,
        deck.wins,
        deck.losses,
        deck.win_rate,
        deck.cube_rate,
    )


def list_decks(limit: int = 1000) -> List[Dict]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM decks
            ORDER BY datetime(first_seen) DESC, win_rate DESC, matches DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["cards"] = json.loads(item.pop("cards_json"))
        result.append(item)
    return result


def stats() -> Dict:
    with closing(connect()) as conn:
        total = conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0]
        observations = conn.execute("SELECT COUNT(*) FROM deck_observations").fetchone()[0]
        latest = conn.execute(
            "SELECT finished_at, status, fetched_count, inserted_count, updated_count, message FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "mazos_unicos": int(total),
        "observaciones": int(observations),
        "ultima_ejecucion": dict(latest) if latest else None,
    }

