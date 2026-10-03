from django.core.management.base import BaseCommand
from monitor.services import collect_now

class Command(BaseCommand):
    help = "Collect shortage signals into the Django/PostgreSQL database."

    def handle(self, *args, **options):
        run = collect_now()
        self.stdout.write(
            self.style.SUCCESS(
                f"Collection complete: seen={run.seen} new={run.new} errors={len(run.errors)}"
            )
        )
