from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


TELEGRAM_API_BASE = "https://api.telegram.org"
RELEVANT_CATEGORIES = ("candidate", "review", "resolved")
CATEGORY_LABELS = {
    "candidate": "کمبود احتمالی",
    "review": "نیازمند بررسی",
    "resolved": "رفع کمبود",
}


class TelegramError(RuntimeError):
    """Safe Telegram error that never includes the bot token."""


def build_digest(report: dict[str, Any], limit: int = 8) -> str | None:
    candidates = [
        item
        for item in report.get("items", [])
        if item.get("category") in RELEVANT_CATEGORIES
    ]
    if not candidates:
        return None

    lines = [
        "گزارش پایش کمبود دارو",
        f"خبرهای تازه: {report.get('new_signals', 0)} | نیازمند بررسی: {len(candidates)}",
    ]

    for item in candidates[:limit]:
        category = item.get("category")
        label = CATEGORY_LABELS.get(category, "نیازمند بررسی")
        lines.append(
            f"• {label}: {item.get('title', 'بدون عنوان')} "
            f"({item.get('source', 'نامشخص')})"
        )
        if item.get("url"):
            lines.append(str(item["url"]))

    if len(candidates) > limit:
        lines.append(f"و {len(candidates) - limit} خبر دیگر")

    errors = report.get("errors") or []
    if errors:
        failed_sources = [str(e.get("source", "نامشخص")) for e in errors]
        lines.append("منابع ناموفق: " + ", ".join(failed_sources))

    lines.append("این گزارش خودکار است؛ کمبودها تأیید نشده‌اند.")
    return "\n".join(lines)[:4000]


@dataclass(slots=True)
class TelegramClient:
    token: str
    timeout: float = 15.0

    def __post_init__(self) -> None:
        self.token = self.token.strip()
        if not self.token:
            raise TelegramError("TELEGRAM_BOT_TOKEN is not configured")

    def _call(self, method: str, payload: dict[str, Any] | None = None, request_timeout: float | None = None) -> Any:
        try:
            response = httpx.post(
                f"{TELEGRAM_API_BASE}/bot{self.token}/{method}",
                json=payload or {},
                timeout=request_timeout or self.timeout,
            )
        except httpx.HTTPError:
            raise TelegramError("Telegram request failed; check network access") from None

        try:
            data = response.json()
        except ValueError:
            raise TelegramError("Telegram returned an invalid response") from None

        if response.status_code != 200 or not data.get("ok"):
            description = data.get("description") or "Telegram rejected the request"
            raise TelegramError(str(description))
        return data.get("result")

    def get_me(self) -> dict[str, Any]:
        result = self._call("getMe")
        return result if isinstance(result, dict) else {}

    def get_chat(self, chat_id: str) -> dict[str, Any]:
        result = self._call("getChat", {"chat_id": chat_id})
        return result if isinstance(result, dict) else {}

    def get_updates(self, offset: int | None = None, timeout: int = 25) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            payload["offset"] = offset
        result = self._call("getUpdates", payload, request_timeout=max(self.timeout, timeout + 10))
        return result if isinstance(result, list) else []

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        self._call(
            "answerCallbackQuery",
            {"callback_query_id": callback_query_id, "text": text[:180]},
        )

    def edit_message_text(
        self,
        chat_id: str | int,
        message_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[:4000],
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        result = self._call("editMessageText", payload)
        return result if isinstance(result, dict) else {}

    def send_message(
        self,
        chat_id: str | int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if isinstance(chat_id, str) and not chat_id.strip():
            raise TelegramError("TELEGRAM_CHAT_ID is not configured")

        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text[:4000],
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        result = self._call(
            "sendMessage",
            payload,
        )
        return result if isinstance(result, dict) else {}
