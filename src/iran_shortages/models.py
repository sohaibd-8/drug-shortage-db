from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Optional

@dataclass
class ShortageSignal:
    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    summary: str = ""
    drug_name: Optional[str] = None
    status: str = "reported"
    country: str = "IR"
    source_kind: str = "news"

    @property
    def fingerprint(self) -> str:
        base = f"{self.source}|{self.url}|{self.title}".strip().lower()
        return sha256(base.encode("utf-8")).hexdigest()

    def to_dict(self):
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        return d
