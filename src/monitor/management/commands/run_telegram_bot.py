from django.core.management.base import BaseCommand
from monitor.telegram_admin import run_admin_bot


class Command(BaseCommand):
    help = "Run the Telegram bot with an in-bot admin panel."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Telegram admin bot"))
        run_admin_bot()
