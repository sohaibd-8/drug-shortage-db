from django.utils import timezone
from iran_shortages.analysis import analyze
from iran_shortages.config import SOURCES
from iran_shortages.sources.rss import fetch_rss
from iran_shortages.sources.html_list import fetch_news_page
from .models import CollectionRun, Signal, Source

COLLECTORS = {"rss": fetch_rss, "html": fetch_news_page}

def sync_sources():
    for cfg in SOURCES:
        Source.objects.update_or_create(
            name=cfg["name"],
            defaults={
                "kind": cfg["kind"],
                "url": cfg["url"],
                "fallback_url": cfg.get("fallback_url",""),
                "enabled": cfg.get("enabled", True),
            },
        )

def collect_now():
    sync_sources()
    run = CollectionRun.objects.create()
    seen = new = 0
    errors = []

    for src in Source.objects.filter(enabled=True):
        try:
            items = COLLECTORS[src.kind](src.url, src.name)
            seen += len(items)
            for item in items:
                result = analyze(item.title, item.summary)
                obj, created = Signal.objects.update_or_create(
                    fingerprint=item.fingerprint,
                    defaults={
                        "title": item.title,
                        "url": item.url,
                        "source": item.source,
                        "published_at": item.published_at or "",
                        "summary": item.summary or "",
                        "drug_name": item.drug_name or "",
                        "category": result["category"],
                        "reason": result["reason"],
                    },
                )
                new += int(created)
            src.last_status = "ok"
            src.last_error = ""
        except Exception as exc:
            src.last_status = "error"
            src.last_error = str(exc)[:1000]
            errors.append({"source": src.name, "error": str(exc)})
        src.last_checked_at = timezone.now()
        src.save(update_fields=["last_status","last_error","last_checked_at"])

    run.finished_at = timezone.now()
    run.seen = seen
    run.new = new
    run.errors = errors
    run.save(update_fields=["finished_at","seen","new","errors"])
    return run
