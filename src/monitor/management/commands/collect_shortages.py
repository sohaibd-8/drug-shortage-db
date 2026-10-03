import os

from django.core.management.base import BaseCommand

from iran_shortages.telegram import TelegramClient, TelegramError
from monitor.reporting import send_run_report
from monitor.services import collect_now


class Command(BaseCommand):
    help = "Collect shortage signals and optionally send a professional Telegram report."

    def handle(self, *args, **options):
        run = collect_now()
        self.stdout.write(
            self.style.SUCCESS(
                f"Collection complete: seen={run.seen} new={run.new} errors={len(run.errors)}"
            )
        )

        enabled = os.getenv("TELEGRAM_REPORTS_ENABLED", "1").strip().lower()
        if enabled in {"0", "false", "no", "off"}:
            return

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            self.stdout.write(
                self.style.WARNING(
                    "Telegram report skipped: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured"
                )
            )
            return

        try:
            max_items = int(os.getenv("TELEGRAM_REPORT_MAX_ITEMS", "20"))
        except ValueError:
            max_items = 20

        try:
            send_run_report(
                run,
                TelegramClient(token),
                chat_id,
                max_items=max(1, min(max_items, 50)),
            )
            self.stdout.write(self.style.SUCCESS("Professional Telegram report sent"))
        except TelegramError as exc:
            self.stderr.write(self.style.ERROR(f"Telegram report failed: {exc}"))
