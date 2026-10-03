from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from ..models import ShortageSignal
from ..classifier import is_shortage_signal, guess_drug_name
from .rss import DEFAULT_HEADERS

# Generic fallback for Persian news pages. Site-specific adapters can replace this
# once DOM structure is verified and stabilized.
def fetch_news_page(url: str, source: str) -> list[ShortageSignal]:
    with httpx.Client(timeout=30, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        r = client.get(url)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text(" ", strip=True).split())
        if len(title) < 8 or not is_shortage_signal(title):
            continue
        link = urljoin(str(r.url), a["href"])
        key = (title, link)
        if key in seen:
            continue
        seen.add(key)
        out.append(ShortageSignal(
            title=title, url=link, source=source,
            drug_name=guess_drug_name(title), source_kind="html"
        ))
    return out
