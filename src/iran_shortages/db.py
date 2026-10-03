import sqlite3
from pathlib import Path
from .models import ShortageSignal

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
  fingerprint TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source TEXT NOT NULL,
  published_at TEXT,
  summary TEXT,
  drug_name TEXT,
  status TEXT NOT NULL,
  country TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_signals_drug ON signals(drug_name);
CREATE INDEX IF NOT EXISTS idx_signals_published ON signals(published_at);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE TABLE IF NOT EXISTS collection_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  signals_seen INTEGER NOT NULL DEFAULT 0,
  new_signals INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS source_runs (
  run_id INTEGER NOT NULL REFERENCES collection_runs(id),
  source TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('ok', 'error')),
  signals_seen INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  PRIMARY KEY (run_id, source)
);
CREATE TABLE IF NOT EXISTS signal_observations (
  run_id INTEGER NOT NULL REFERENCES collection_runs(id),
  fingerprint TEXT NOT NULL REFERENCES signals(fingerprint),
  category TEXT NOT NULL,
  analysis_version TEXT NOT NULL,
  observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (run_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_observations_fingerprint ON signal_observations(fingerprint);
CREATE TABLE IF NOT EXISTS review_labels (
  fingerprint TEXT PRIMARY KEY REFERENCES signals(fingerprint),
  label TEXT NOT NULL CHECK(label IN ('confirmed_shortage', 'not_shortage', 'resolved', 'uncertain')),
  corrected_drug_name TEXT,
  note TEXT,
  reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

def connect(path: str = "data/shortages.sqlite3"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con

def upsert(con, signal: ShortageSignal) -> bool:
    d = signal.to_dict()
    cur = con.execute("SELECT 1 FROM signals WHERE fingerprint=?", (d["fingerprint"],))
    exists = cur.fetchone() is not None
    con.execute(
        """INSERT INTO signals
        (fingerprint,title,url,source,published_at,summary,drug_name,status,country,source_kind)
        VALUES (:fingerprint,:title,:url,:source,:published_at,:summary,:drug_name,:status,:country,:source_kind)
        ON CONFLICT(fingerprint) DO UPDATE SET
          last_seen_at=CURRENT_TIMESTAMP,
          published_at=COALESCE(excluded.published_at, signals.published_at),
          summary=CASE WHEN length(excluded.summary)>length(signals.summary) THEN excluded.summary ELSE signals.summary END,
          drug_name=COALESCE(signals.drug_name, excluded.drug_name)
        """, d
    )
    con.commit()
    return not exists


def start_run(con) -> int:
    run_id = con.execute("INSERT INTO collection_runs DEFAULT VALUES").lastrowid
    con.commit()
    return run_id


def record_source(con, run_id: int, source: str, status: str, count: int, error: str | None = None):
    con.execute(
        "INSERT INTO source_runs(run_id, source, status, signals_seen, error) VALUES (?, ?, ?, ?, ?)",
        (run_id, source, status, count, error),
    )
    con.commit()


def record_observation(con, run_id: int, fingerprint: str, category: str):
    con.execute(
        "INSERT INTO signal_observations(run_id, fingerprint, category, analysis_version) VALUES (?, ?, ?, ?)",
        (run_id, fingerprint, category, "rules-v1"),
    )
    con.commit()


def finish_run(con, run_id: int, seen: int, new: int):
    con.execute(
        "UPDATE collection_runs SET finished_at=CURRENT_TIMESTAMP, signals_seen=?, new_signals=? WHERE id=?",
        (seen, new, run_id),
    )
    con.commit()
