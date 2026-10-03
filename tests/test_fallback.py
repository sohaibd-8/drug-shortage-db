import httpx

from iran_shortages import pipeline
from iran_shortages.db import connect
from iran_shortages.models import ShortageSignal


def test_rss_http_failure_uses_homepage_and_records_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SOURCES", [{
        "name": "MedUnited", "kind": "rss", "url": "https://medunited.ir/rss.xml",
        "fallback_url": "https://medunited.ir/", "enabled": True,
    }])

    def fail_rss(url, source):
        raise httpx.HTTPStatusError("404", request=httpx.Request("GET", url), response=httpx.Response(404))

    monkeypatch.setattr(pipeline, "fetch_rss", fail_rss)
    monkeypatch.setitem(pipeline.COLLECTORS, "rss", fail_rss)
    monkeypatch.setattr(pipeline, "fetch_news_page", lambda url, source: [
        ShortageSignal(title="کمبود قرص الف", url="https://medunited.ir/a", source=source)
    ])
    db_path = str(tmp_path / "shortages.sqlite3")
    stats, report = pipeline.run(db_path, with_report=True)
    assert stats["fallback_sources"] == ["MedUnited"]
    assert report["categories"] == {"candidate": 1}
    con = connect(db_path)
    assert con.execute("SELECT status, signals_seen FROM source_runs").fetchone() == ("fallback", 1)
    con.close()
