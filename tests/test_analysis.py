from iran_shortages.analysis import analyze, make_report


def test_triage_separates_foreign_context_and_candidate():
    assert analyze("کمبود داپسون در استرالیا")["category"] == "foreign"
    assert analyze("قیمت دارو تحت تأثیر ارز است", "کمبود پزشک")["category"] == "context"
    assert analyze("رفع کمبود داروی الف")["category"] == "resolved"
    assert analyze("از کمبود «مایفورتیک» تا مشکلات بیماران")["category"] == "candidate"
    assert analyze("مدیریت کمبودهای جاری")["category"] == "review"


def test_report_counts_new_signals_and_source_failures():
    stats = {
        "sources": 3, "seen": 2, "new": 1,
        "source_counts": {"MedUnited": 2, "IFDANA": None},
        "errors": [{"source": "IFDANA", "error": "timed out"}],
    }
    report = make_report(stats, [{"title": "کمبود قرص الف", "summary": "", "source": "MedUnited", "url": "https://example.org/a"}])
    assert report["categories"] == {"candidate": 1}
    assert report["source_counts"]["IFDANA"] is None
    assert report["new_signals"] == 1
    assert report["fallback_sources"] == []
