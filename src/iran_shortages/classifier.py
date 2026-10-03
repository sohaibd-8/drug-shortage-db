import re

# Conservative first-pass lexicon. This intentionally favors precision over recall.
KEYWORDS = (
    "کمبود", "ناموجود", "عدم موجودی", "تأمین دارو", "تامين دارو",
    "دچار کمبود", "رفع کمبود", "کمبود دارو", "موجودی دارو",
    "shortage", "out of stock", "supply disruption",
)

EXCLUDE = (
    "کمبود خواب", "کمبود ویتامین", "کمبود آهن", "کمبود وزن",
)

def is_shortage_signal(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}".lower()
    if any(x.lower() in text for x in EXCLUDE):
        return False
    return any(k.lower() in text for k in KEYWORDS)

DRUG_PATTERNS = [
    re.compile(r"کمبود\s+([\u0600-\u06FFa-zA-Z0-9\-‌ ]{2,60}?)(?:[؛،,.]|$|\s+و\s+)", re.I),
    re.compile(r"(?:داروی|داروهای)\s+([\u0600-\u06FFa-zA-Z0-9\-‌ ]{2,60}?)(?:[؛،,.]|$)", re.I),
]

def guess_drug_name(title: str) -> str | None:
    for pat in DRUG_PATTERNS:
        m = pat.search(title)
        if m:
            value = " ".join(m.group(1).split()).strip(" -–—")
            if value:
                return value
    return None
