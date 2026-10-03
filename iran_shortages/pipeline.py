from .config import SOURCES
from .db import connect, upsert
from .sources.rss import fetch_rss
from .sources.html_list import fetch_news_page

COLLECTORS = {"rss": fetch_rss, "html": fetch_news_page}

def run(db_path="data/shortages.sqlite3"):
    con = connect(db_path)
    stats = {"sources": 0, "seen": 0, "new": 0, "errors": []}
    try:
        for src in SOURCES:
            if not src.get("enabled") or not src.get("url"):
                continue
            stats["sources"] += 1
            try:
                items = COLLECTORS[src["kind"]](src["url"], src["name"])
                stats["seen"] += len(items)
                for item in items:
                    if upsert(con, item):
                        stats["new"] += 1
            except Exception as e:
                stats["errors"].append({"source": src["name"], "error": str(e)})
    finally:
        con.close()
    return stats
