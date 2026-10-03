from __future__ import annotations

import os
import time
from typing import Any

from iran_shortages.telegram import TelegramClient, TelegramError
from .models import CollectionRun, Signal, Source
from .services import collect_now, sync_sources


def parse_admin_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    result: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        value = part.strip()
        if not value:
            continue
        try:
            result.add(int(value))
        except ValueError:
            continue
    return result


def _kb(rows: list[list[tuple[str, str]]]) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": data} for text, data in row]
            for row in rows
        ]
    }


def _dashboard_text() -> str:
    total = Signal.objects.count()
    review = Signal.objects.filter(category__in=["candidate", "review"]).count()
    confirmed = Signal.objects.filter(review_label="confirmed_shortage").count()
    sources = Source.objects.filter(enabled=True).count()
    last = CollectionRun.objects.first()
    last_line = "هنوز اجرا نشده"
    if last:
        last_line = f"{last.started_at:%Y-%m-%d %H:%M} | دیده‌شده {last.seen} | جدید {last.new}"
    return (
        "🛠 پنل مدیریت ربات پایش کمبود دارو\n\n"
        f"📊 کل سیگنال‌ها: {total}\n"
        f"🟠 نیازمند بررسی: {review}\n"
        f"✅ تأییدشده: {confirmed}\n"
        f"🌐 منابع فعال: {sources}\n"
        f"🕒 آخرین پایش: {last_line}"
    )


def _main_menu() -> tuple[str, dict[str, Any]]:
    return _dashboard_text(), _kb([
        [("📰 بررسی سیگنال‌ها", "adm:signals:0"), ("📡 منابع", "adm:sources")],
        [("▶️ اجرای پایش الآن", "adm:collect"), ("📈 آمار", "adm:stats")],
        [("🔄 تازه‌سازی", "adm:home")],
    ])


def _signals_page(page: int, page_size: int = 5) -> tuple[str, dict[str, Any]]:
    qs = Signal.objects.filter(category__in=["candidate", "review"]).order_by("-first_seen_at")
    total = qs.count()
    page = max(page, 0)
    items = list(qs[page * page_size:(page + 1) * page_size])
    lines = [f"📰 سیگنال‌های نیازمند بررسی — {total} مورد\n"]
    rows: list[list[tuple[str, str]]] = []
    for item in items:
        drug = item.corrected_drug_name or item.drug_name or "نامشخص"
        lines.append(f"• #{item.id} | {drug}\n{item.title[:160]}\n")
        rows.append([(f"باز کردن #{item.id}", f"adm:signal:{item.id}:{page}")])
    nav: list[tuple[str, str]] = []
    if page > 0:
        nav.append(("⬅️ قبلی", f"adm:signals:{page-1}"))
    if (page + 1) * page_size < total:
        nav.append(("بعدی ➡️", f"adm:signals:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([("🏠 منوی مدیریت", "adm:home")])
    if not items:
        lines.append("موردی برای بررسی وجود ندارد.")
    return "\n".join(lines)[:3900], _kb(rows)


def _signal_detail(signal_id: int, page: int = 0) -> tuple[str, dict[str, Any]]:
    item = Signal.objects.get(pk=signal_id)
    drug = item.corrected_drug_name or item.drug_name or "نامشخص"
    review = item.get_review_label_display() if item.review_label else "بررسی نشده"
    text = (
        f"📰 سیگنال #{item.id}\n\n"
        f"💊 دارو: {drug}\n"
        f"🏷 دسته: {item.get_category_display()}\n"
        f"🔎 وضعیت بررسی: {review}\n"
        f"📡 منبع: {item.source}\n\n"
        f"{item.title}\n\n"
        f"{item.reason or ''}\n"
        f"{item.url}"
    )
    keyboard = _kb([
        [("✅ تأیید کمبود", f"adm:label:{item.id}:confirmed_shortage:{page}")],
        [("❌ کمبود نیست", f"adm:label:{item.id}:not_shortage:{page}")],
        [("🟢 رفع شده", f"adm:label:{item.id}:resolved:{page}"),
         ("❓ نامشخص", f"adm:label:{item.id}:uncertain:{page}")],
        [("⬅️ فهرست", f"adm:signals:{page}"), ("🏠 مدیریت", "adm:home")],
    ])
    return text[:3900], keyboard


def _sources_text() -> tuple[str, dict[str, Any]]:
    sync_sources()
    sources = list(Source.objects.order_by("name"))
    lines = ["📡 مدیریت منابع\n"]
    rows: list[list[tuple[str, str]]] = []
    for src in sources:
        icon = "🟢" if src.enabled else "⚪️"
        status = src.last_status or "—"
        lines.append(f"{icon} {src.name} | {status}")
        rows.append([(f"{icon} {src.name[:32]}", f"adm:source:{src.id}")])
    rows.append([("🏠 منوی مدیریت", "adm:home")])
    return "\n".join(lines)[:3900], _kb(rows)


def _stats_text() -> tuple[str, dict[str, Any]]:
    counts = {
        key: Signal.objects.filter(category=key).count()
        for key in ["candidate", "review", "resolved", "foreign", "context"]
    }
    reviewed = Signal.objects.exclude(review_label="").count()
    text = (
        "📈 آمار پایگاه\n\n"
        f"کمبود احتمالی: {counts['candidate']}\n"
        f"نیازمند بررسی: {counts['review']}\n"
        f"رفع کمبود: {counts['resolved']}\n"
        f"خارجی: {counts['foreign']}\n"
        f"زمینه‌ای: {counts['context']}\n"
        f"بررسی دستی‌شده: {reviewed}"
    )
    return text, _kb([[("🏠 منوی مدیریت", "adm:home")]])


class TelegramAdminBot:
    def __init__(self, token: str, admin_ids: set[int]) -> None:
        if not admin_ids:
            raise RuntimeError("TELEGRAM_ADMIN_IDS is not configured")
        self.client = TelegramClient(token)
        self.admin_ids = admin_ids
        self.offset: int | None = None

    def _authorized(self, user_id: int | None) -> bool:
        return bool(user_id and user_id in self.admin_ids)

    def _send_home(self, chat_id: int) -> None:
        text, markup = _main_menu()
        self.client.send_message(chat_id, text, markup)

    def _edit(self, chat_id: int, message_id: int, text: str, markup: dict[str, Any]) -> None:
        try:
            self.client.edit_message_text(chat_id, message_id, text, markup)
        except TelegramError as exc:
            if "message is not modified" not in str(exc).lower():
                self.client.send_message(chat_id, text, markup)

    def handle_message(self, message: dict[str, Any]) -> None:
        user_id = (message.get("from") or {}).get("id")
        chat_id = (message.get("chat") or {}).get("id")
        text = str(message.get("text") or "").strip()
        if not isinstance(chat_id, int):
            return
        if text.startswith("/admin") or text.startswith("/start"):
            if not self._authorized(user_id):
                self.client.send_message(chat_id, "⛔️ دسترسی به پنل مدیریت برای این حساب فعال نیست.")
                return
            self._send_home(chat_id)

    def handle_callback(self, callback: dict[str, Any]) -> None:
        user_id = (callback.get("from") or {}).get("id")
        callback_id = str(callback.get("id") or "")
        if not self._authorized(user_id):
            if callback_id:
                self.client.answer_callback_query(callback_id, "دسترسی ندارید.")
            return

        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        message_id = message.get("message_id")
        data = str(callback.get("data") or "")
        if not isinstance(chat_id, int) or not isinstance(message_id, int):
            return

        try:
            if data == "adm:home":
                text, markup = _main_menu()
            elif data == "adm:collect":
                if callback_id:
                    self.client.answer_callback_query(callback_id, "پایش شروع شد…")
                    callback_id = ""
                run = collect_now()
                text, markup = _main_menu()
                text += f"\n\n✅ اجرا تمام شد: {run.seen} مورد دیده شد، {run.new} مورد جدید."
            elif data.startswith("adm:signals:"):
                page = int(data.rsplit(":", 1)[1])
                text, markup = _signals_page(page)
            elif data.startswith("adm:signal:"):
                _, _, signal_id, page = data.split(":")
                text, markup = _signal_detail(int(signal_id), int(page))
            elif data.startswith("adm:label:"):
                _, _, signal_id, label, page = data.split(":")
                Signal.objects.filter(pk=int(signal_id)).update(review_label=label)
                text, markup = _signal_detail(int(signal_id), int(page))
            elif data == "adm:sources":
                text, markup = _sources_text()
            elif data.startswith("adm:source:"):
                source_id = int(data.rsplit(":", 1)[1])
                src = Source.objects.get(pk=source_id)
                src.enabled = not src.enabled
                src.save(update_fields=["enabled"])
                text, markup = _sources_text()
            elif data == "adm:stats":
                text, markup = _stats_text()
            else:
                text, markup = _main_menu()
            self._edit(chat_id, message_id, text, markup)
            if callback_id:
                self.client.answer_callback_query(callback_id)
        except (Signal.DoesNotExist, Source.DoesNotExist, ValueError):
            if callback_id:
                self.client.answer_callback_query(callback_id, "این مورد دیگر موجود نیست.")
        except Exception:
            if callback_id:
                self.client.answer_callback_query(callback_id, "خطا در اجرای دستور.")

    def run_forever(self) -> None:
        while True:
            try:
                updates = self.client.get_updates(self.offset, timeout=25)
                for update in updates:
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        self.offset = update_id + 1
                    if isinstance(update.get("message"), dict):
                        self.handle_message(update["message"])
                    elif isinstance(update.get("callback_query"), dict):
                        self.handle_callback(update["callback_query"])
            except TelegramError:
                time.sleep(3)
            except Exception:
                time.sleep(2)


def run_admin_bot() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    admin_ids = parse_admin_ids(os.getenv("TELEGRAM_ADMIN_IDS"))
    TelegramAdminBot(token, admin_ids).run_forever()
