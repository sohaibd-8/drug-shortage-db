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
