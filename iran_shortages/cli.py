import argparse, json, sqlite3
from .pipeline import run
from .db import connect

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--db", default="data/shortages.sqlite3")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--db", default="data/shortages.sqlite3")
    args = p.parse_args()
    if args.cmd == "run":
        print(json.dumps(run(args.db), ensure_ascii=False, indent=2))
    else:
        con = connect(args.db)
        q = f"%{args.query}%"
        rows = con.execute(
            "SELECT title,url,source,published_at,drug_name,status FROM signals WHERE title LIKE ? OR drug_name LIKE ? ORDER BY COALESCE(published_at, first_seen_at) DESC LIMIT 50",
            (q,q),
        ).fetchall()
        con.close()
        print(json.dumps(rows, ensure_ascii=False, indent=2))
