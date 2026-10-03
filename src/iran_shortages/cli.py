import argparse
import json
import os
from pathlib import Path

from .db import connect
from .pipeline import run
from .telegram import TelegramClient, TelegramError, build_digest


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--db", default="data/shortages.sqlite3")
    r.add_argument("--report", help="Save analysis of new signals as JSON")

    n = sub.add_parser("notify")
    n.add_argument("--report", default="data/latest-report.json")
    n.add_argument("--dry-run", action="store_true")

    c = sub.add_parser("telegram-check")
    c.add_argument("--chat-id", help="Optional chat ID to validate; defaults to TELEGRAM_CHAT_ID")

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--db", default="data/shortages.sqlite3")

    args = p.parse_args()

    if args.cmd == "run":
        if args.report:
            stats, report = run(args.db, with_report=True)
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            stats = run(args.db)

        print(json.dumps(stats, ensure_ascii=False, indent=2))
        if stats["sources"] and len(stats["errors"]) == stats["sources"]:
            raise SystemExit(1)

    elif args.cmd == "notify":
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        message = build_digest(report)
        if not message:
            print("No new relevant signals to notify")
            return

        if args.dry_run:
            print(message)
            return

        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        try:
            TelegramClient(token).send_message(chat_id, message)
        except TelegramError as exc:
            raise SystemExit(str(exc)) from None

        print("Telegram digest sent")

    elif args.cmd == "telegram-check":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

        try:
            client = TelegramClient(token)
            bot = client.get_me()
            result = {
                "ok": True,
                "bot_id": bot.get("id"),
                "username": bot.get("username"),
                "name": bot.get("first_name"),
            }
            if chat_id:
                chat = client.get_chat(chat_id)
                result["chat"] = {
                    "id": chat.get("id"),
                    "type": chat.get("type"),
                    "title": chat.get("title")
                    or chat.get("username")
                    or chat.get("first_name"),
                }
        except TelegramError as exc:
            raise SystemExit(str(exc)) from None

        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        con = connect(args.db)
        q = f"%{args.query}%"
        rows = con.execute(
            "SELECT title,url,source,published_at,drug_name,status "
            "FROM signals "
            "WHERE title LIKE ? OR drug_name LIKE ? "
            "ORDER BY COALESCE(published_at, first_seen_at) DESC LIMIT 50",
            (q, q),
        ).fetchall()
        con.close()
        print(json.dumps(rows, ensure_ascii=False, indent=2))
