"""Conservative, explainable triage of collected news signals."""

from collections import Counter
from datetime import datetime, timezone
import re


FOREIGN_MARKERS = ("استرالیا", "tga", "آمریکا", "ایالات متحده", "کانادا", "انگلستان")
RESOLVED_MARKERS = ("رفع کمبود", "برطرف شدن کمبود", "کمبود برطرف", "پایان کمبود")
SHORTAGE_MARKERS = ("کمبود", "ناموجود", "عدم موجودی", "supply disruption", "shortage")
DRUG_CUES = ("داروی «", "داروهای «", "قرص ", "کپسول ", "آمپول ", "ویال ")


def analyze(title: str, summary: str = "") -> dict[str, str]:
    """Classify relevance, never claim that a shortage is verified."""
    headline = " ".join(title.lower().split())
    detail = f"{headline} {summary.lower()}"
    if any(marker in headline for marker in FOREIGN_MARKERS):
        return {"category": "foreign", "reason": "خبر درباره کشور دیگری است"}
    if any(marker in headline for marker in RESOLVED_MARKERS):
        return {"category": "resolved", "reason": "عنوان از رفع کمبود می‌گوید"}
    if "کمبود ندار" in headline or "بدون کمبود" in headline:
        return {"category": "context", "reason": "عنوان وقوع کمبود را تأیید نمی‌کند"}
    if not any(marker in headline for marker in SHORTAGE_MARKERS):
        return {"category": "context", "reason": "کمبود در عنوان خبر مطرح نشده است"}
    if any(cue in headline for cue in DRUG_CUES) or re.search(r"کمبود\s+[«\"].+?[»\"]", headline):
        return {"category": "candidate", "reason": "عنوان به کمبود داروی مشخص اشاره می‌کند؛ نیازمند بررسی"}
    if "کمبود" in detail:
        return {"category": "review", "reason": "خبر درباره کمبود است، اما داروی مشخصی در عنوان ندارد"}
    return {"category": "context", "reason": "ارتباط با کمبود دارویی روشن نیست"}


def make_report(stats: dict, items: list[dict]) -> dict:
    analyzed = [
        {
            "title": item["title"],
            "url": item["url"],
            "source": item["source"],
            **analyze(item["title"], item.get("summary") or ""),
        }
        for item in items
    ]
    counts = Counter(item["category"] for item in analyzed)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_checked": stats["sources"],
        "signals_seen": stats["seen"],
        "new_signals": stats["new"],
        "categories": dict(counts),
        "source_counts": stats["source_counts"],
        "fallback_sources": stats.get("fallback_sources", []),
        "errors": stats["errors"],
        "items": analyzed,
        "note": "دسته‌بندی خودکار است و تأیید کمبود فعلی محسوب نمی‌شود.",
    }
