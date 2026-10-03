import pytest

from iran_shortages.telegram import TelegramClient, TelegramError, build_digest


def test_build_digest_filters_irrelevant_items():
    report = {
        "new_signals": 3,
        "items": [
            {
                "category": "candidate",
                "title": "کمبود داروی «الف»",
                "source": "A",
                "url": "https://a",
            },
            {
                "category": "context",
                "title": "خبر زمینه‌ای",
                "source": "B",
                "url": "https://b",
            },
            {
                "category": "resolved",
                "title": "رفع کمبود ب",
                "source": "C",
                "url": "https://c",
            },
        ],
        "errors": [],
    }

    message = build_digest(report)

    assert message is not None
    assert "کمبود داروی «الف»" in message
    assert "رفع کمبود ب" in message
    assert "خبر زمینه‌ای" not in message


def test_build_digest_returns_none_without_relevant_items():
    assert build_digest({"items": [{"category": "context"}]}) is None


def test_client_rejects_blank_token():
    with pytest.raises(TelegramError):
        TelegramClient("   ")
