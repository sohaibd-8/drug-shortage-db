import httpx

from iran_shortages.sources.html_list import fetch_news_page
from iran_shortages.sources.rss import fetch_rss


def mock_client(monkeypatch, body):
    real_client = httpx.Client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=body, request=request)
    )
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )


def test_medunited_rss_parsing(monkeypatch):
    mock_client(
        monkeypatch,
        """<rss version="2.0"><channel><title>MedUnited</title>
        <item><title>کمبود سوتالول؛ علت چیست؟</title>
        <link>https://medunited.ir/news/1</link></item>
        </channel></rss>""",
    )
    signals = fetch_rss("https://medunited.ir/rss.xml", "MedUnited")
    assert len(signals) == 1
    assert signals[0].drug_name == "سوتالول"
    assert signals[0].url == "https://medunited.ir/news/1"


def test_html_news_parsing(monkeypatch):
    mock_client(
        monkeypatch,
        '<a href="/news/1">کمبود داروی سوتالول در بازار</a>',
    )
    signals = fetch_news_page("https://ifdana.fda.gov.ir/", "IFDANA")
    assert len(signals) == 1
    assert signals[0].url == "https://ifdana.fda.gov.ir/news/1"
    assert signals[0].source_kind == "html"
