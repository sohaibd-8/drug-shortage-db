import feedparser
import httpx
from ..models import ShortageSignal
from ..classifier import is_shortage_signal, guess_drug_name

DEFAULT_HEADERS = {"User-Agent": "IranDrugShortageDB/0.1 (+public-health research)"}

def fetch_rss(url: str, source: str) -> list[ShortageSignal]:
    with httpx.Client(timeout=30, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        r = client.get(url)
        r.raise_for_status()
    feed = feedparser.parse(r.content)
    out = []
    for e in feed.entries:
        title = getattr(e, "title", "").strip()
        summary = getattr(e, "summary", "") or ""
        if not is_shortage_signal(title, summary):
            continue
        out.append(ShortageSignal(
            title=title,
            url=getattr(e, "link", ""),
            source=source,
            published_at=getattr(e, "published", None) or getattr(e, "updated", None),
            summary=summary,
            drug_name=guess_drug_name(title),
            source_kind="rss",
        ))
    return out
