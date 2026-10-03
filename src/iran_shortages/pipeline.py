from .config import SOURCES
from .db import connect, upsert, start_run, record_source, record_observation, finish_run
from .sources.rss import fetch_rss
from .sources.html_list import fetch_news_page
from .analysis import analyze, make_report
import httpx

COLLECTORS = {"rss": fetch_rss, "html": fetch_news_page}

def run(db_path="data/shortages.sqlite3", with_report=False):
    con = connect(db_path)
    stats = {"sources": 0, "seen": 0, "new": 0, "errors": [], "source_counts": {}, "fallback_sources": []}
    new_items = []
    run_id = start_run(con)
    stats["run_id"] = run_id
    try:
        for src in SOURCES:
            if not src.get("enabled") or not src.get("url"):
                continue
            stats["sources"] += 1
            try:
                mode = "ok"
                try:
                    items = COLLECTORS[src["kind"]](src["url"], src["name"])
                except httpx.HTTPError:
                    if not src.get("fallback_url"):
                        raise
                    items = fetch_news_page(src["fallback_url"], src["name"])
                    mode = "fallback"
                    stats["fallback_sources"].append(src["name"])
                stats["seen"] += len(items)
                stats["source_counts"][src["name"]] = len(items)
                for item in items:
                    if upsert(con, item):
                        stats["new"] += 1
                        new_items.append(item.to_dict())
                    record_observation(con, run_id, item.fingerprint, analyze(item.title, item.summary)["category"])
                record_source(con, run_id, src["name"], mode, len(items))
            except Exception as e:
                stats["source_counts"][src["name"]] = None
                stats["errors"].append({"source": src["name"], "error": str(e)})
                record_source(con, run_id, src["name"], "error", 0, str(e))
    finally:
        finish_run(con, run_id, stats["seen"], stats["new"])
        con.close()
    return (stats, make_report(stats, new_items)) if with_report else stats
