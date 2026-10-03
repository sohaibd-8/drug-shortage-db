import argparse
import json
import os
from pathlib import Path
import httpx
from .pipeline import run
from .db import connect

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--db", default="data/shortages.sqlite3")
    r.add_argument("--report", help="Save analysis of new signals as JSON")
    n = sub.add_parser("notify")
    n.add_argument("--report", default="data/latest-report.json")
    n.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--db", default="data/shortages.sqlite3")
    args = p.parse_args()
    if args.cmd == "run":
        if args.report:
            stats, report = run(args.db, with_report=True)
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            stats = run(args.db)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        if stats["sources"] and len(stats["errors"]) == stats["sources"]:
            raise SystemExit(1)
    elif args.cmd == "notify":
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        candidates = [i for i in report["items"] if i["category"] in ("candidate", "review", "resolved")]
        if not candidates:
            print("No new relevant signals to notify")
            return
        lines = ["گزارش پایش کمبود دارو", f"خبرهای تازه: {report['new_signals']} | نیازمند بررسی: {len(candidates)}"]
        for item in candidates[:8]:
            label = {"candidate": "کمبود احتمالی", "review": "نیازمند بررسی", "resolved": "رفع کمبود"}[item["category"]]
            lines.extend((f"• {label}: {item['title']} ({item['source']})", item["url"]))
        if len(candidates) > 8:
            lines.append(f"و {len(candidates) - 8} خبر دیگر")
        if report["errors"]:
            lines.append("منابع ناموفق: " + ", ".join(e["source"] for e in report["errors"]))
        lines.append("این گزارش خودکار است؛ کمبودها تأیید نشده‌اند.")
        message = "\n".join(lines)[:4000]
        if args.dry_run:
            print(message)
            return
        token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        try:
            response = httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
                timeout=15,
            )
            if response.status_code != 200 or not response.json().get("ok"):
                raise RuntimeError("Telegram rejected the message; check bot access and chat ID")
        except httpx.HTTPError:
            raise SystemExit("Telegram request failed; check bot access and network") from None
        print("Telegram digest sent")
    else:
        con = connect(args.db)
        q = f"%{args.query}%"
        rows = con.execute(
            "SELECT title,url,source,published_at,drug_name,status FROM signals WHERE title LIKE ? OR drug_name LIKE ? ORDER BY COALESCE(published_at, first_seen_at) DESC LIMIT 50",
            (q,q),
        ).fetchall()
        con.close()
        print(json.dumps(rows, ensure_ascii=False, indent=2))
