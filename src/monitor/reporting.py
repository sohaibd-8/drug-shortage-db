from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Iterable

from django.utils import timezone

from iran_shortages.telegram import TelegramClient
from .models import CollectionRun, Signal, Source


CATEGORY_FA = {
    "candidate": "کمبود احتمالی",
    "review": "نیازمند بررسی",
    "resolved": "رفع کمبود",
    "foreign": "خارجی",
    "context": "زمینه‌ای",
}

REVIEW_FA = {
    "confirmed_shortage": "تأیید کمبود",
    "not_shortage": "کمبود نیست",
    "resolved": "رفع شده",
    "uncertain": "نامشخص",
    "": "بررسی نشده",
}


def _drug_name(signal: Signal) -> str:
    return (signal.corrected_drug_name or signal.drug_name or "").strip()


def _relevant(qs: Iterable[Signal]) -> list[Signal]:
    return [
        item
        for item in qs
        if item.category in {"candidate", "review", "resolved"}
    ]


def _analysis_lines(items: list[Signal]) -> list[str]:
    if not items:
        return ["• در این بازه سیگنال مرتبط جدیدی برای تحلیل ثبت نشده است."]

    by_drug: dict[str, list[Signal]] = defaultdict(list)
    sources = set()
    for item in items:
        sources.add(item.source)
        drug = _drug_name(item)
        if drug:
            by_drug[drug].append(item)

    corroborated: list[tuple[str, int, int]] = []
    for drug, drug_items in by_drug.items():
        source_count = len({item.source for item in drug_items})
        if source_count >= 2:
            corroborated.append((drug, len(drug_items), source_count))
    corroborated.sort(key=lambda row: (row[2], row[1]), reverse=True)

    counts = Counter(item.category for item in items)
    lines = [
        f"• {len(items)} سیگنال مرتبط از {len(sources)} منبع در این بازه ثبت شده است.",
        (
            "• ترکیب سیگنال‌ها: "
            f"{counts.get('candidate', 0)} کمبود احتمالی، "
            f"{counts.get('review', 0)} نیازمند بررسی، "
            f"{counts.get('resolved', 0)} رفع کمبود."
        ),
    ]

    if corroborated:
        top = corroborated[:5]
        summary = "، ".join(
            f"{drug} ({source_count} منبع)"
            for drug, _, source_count in top
        )
        lines.append(
            "• هم‌پوشانی چندمنبعی مشاهده شد: "
            + summary
            + ". این موارد برای بررسی انسانی اولویت بالاتری دارند."
        )
    else:
        lines.append(
            "• هم‌پوشانی چندمنبعی قابل‌اتکا در نام داروها دیده نشد؛ "
            "بیشتر سیگنال‌ها فعلاً تک‌منبعی‌اند."
        )

    unresolved = sum(
        1 for item in items
        if not item.review_label and item.category in {"candidate", "review"}
    )
    if unresolved:
        lines.append(f"• {unresolved} مورد هنوز نیازمند بررسی و تأیید انسانی است.")

    return lines


def _source_health_lines() -> list[str]:
    sources = list(Source.objects.filter(enabled=True).order_by("name"))
    if not sources:
        return ["• هنوز منبع فعالی ثبت نشده است."]

    ok = [s for s in sources if s.last_status == "ok"]
    failed = [s for s in sources if s.last_status == "error"]
    unknown = [s for s in sources if s.last_status not in {"ok", "error"}]

    lines = [f"• سالم: {len(ok)} | خطادار: {len(failed)} | نامشخص: {len(unknown)}"]
    for source in failed[:5]:
        error = (source.last_error or "خطای نامشخص").replace("\n", " ")[:180]
        lines.append(f"• ⚠️ {source.name}: {error}")
    return lines


def _item_block(item: Signal) -> str:
    drug = _drug_name(item) or "نام دارو استخراج نشده"
    review = REVIEW_FA.get(item.review_label, item.review_label or "بررسی نشده")
    label = CATEGORY_FA.get(item.category, item.category)
    lines = [
        f"#{item.id} | {label}",
        f"💊 {drug}",
        f"📰 {item.title[:280]}",
        f"📡 {item.source}",
        f"🔎 بررسی انسانی: {review}",
    ]
    if item.reason:
        lines.append(f"🧠 علت طبقه‌بندی: {item.reason[:220]}")
    if item.url:
        lines.append(f"🔗 {item.url}")
    return "\n".join(lines)


def build_run_report(run: CollectionRun, max_items: int = 20) -> list[str]:
    end = run.finished_at or timezone.now()
    new_items = list(
        Signal.objects.filter(
            first_seen_at__gte=run.started_at,
            first_seen_at__lte=end,
        ).order_by("-first_seen_at")
    )
    relevant = _relevant(new_items)

    counts = Counter(item.category for item in new_items)
    title = "📊 گزارش حرفه‌ای پایش کمبود دارو"
    summary = [
        title,
        "",
        f"🕒 بازه اجرا: {run.started_at:%Y-%m-%d %H:%M} تا {end:%H:%M}",
        f"📥 موارد دیده‌شده: {run.seen}",
        f"🆕 موارد جدید ذخیره‌شده: {run.new}",
        f"🎯 سیگنال‌های مرتبط جدید: {len(relevant)}",
        (
            "🏷 تفکیک کل موارد جدید: "
            f"کمبود احتمالی {counts.get('candidate', 0)} | "
            f"بررسی {counts.get('review', 0)} | "
            f"رفع {counts.get('resolved', 0)} | "
            f"زمینه‌ای {counts.get('context', 0)} | "
            f"خارجی {counts.get('foreign', 0)}"
        ),
        "",
        "🧠 تحلیل خودکار",
        *_analysis_lines(relevant),
        "",
        "📡 سلامت منابع",
        *_source_health_lines(),
        "",
        "⚠️ این تحلیل ماشینی برای اولویت‌بندی و پایش است و جایگزین تأیید انسانی یا اعلام رسمی کمبود نیست.",
    ]
    messages = ["\n".join(summary)[:3900]]

    if relevant:
        shown = relevant[:max_items]
        current = "📰 موارد استخراج‌شده مرتبط\n\n"
        for item in shown:
            block = _item_block(item)
            if len(current) + len(block) + 4 > 3900:
                messages.append(current.rstrip())
                current = "📰 ادامه موارد استخراج‌شده\n\n"
            current += block + "\n\n"
        if current.strip():
            messages.append(current.rstrip())
        if len(relevant) > max_items:
            messages.append(
                f"📌 {len(relevant) - max_items} مورد مرتبط دیگر نیز ثبت شده است؛ "
                "برای بررسی کامل از پنل مدیریت ربات استفاده کنید."
            )
    else:
        messages.append(
            "📰 مورد مرتبط تازه‌ای برای ارسال جزئیات وجود ندارد. "
            "وضعیت منابع و آمار اجرا در گزارش بالا ثبت شده است."
        )
    return messages


def build_recent_report(hours: int = 24, max_items: int = 20) -> list[str]:
    since = timezone.now() - timedelta(hours=hours)
    items = list(Signal.objects.filter(first_seen_at__gte=since).order_by("-first_seen_at"))
    relevant = _relevant(items)
    counts = Counter(item.category for item in items)

    summary = [
        f"📈 گزارش تحلیلی {hours} ساعت اخیر",
        "",
        f"📥 کل موارد جدید: {len(items)}",
        f"🎯 مرتبط با کمبود/رفع کمبود: {len(relevant)}",
        (
            "🏷 ترکیب: "
            f"کمبود احتمالی {counts.get('candidate', 0)} | "
            f"بررسی {counts.get('review', 0)} | "
            f"رفع {counts.get('resolved', 0)}"
        ),
        "",
        "🧠 تحلیل خودکار",
        *_analysis_lines(relevant),
        "",
        "⚠️ تحلیل ماشینی است و نیازمند تأیید انسانی/رسمی است.",
    ]
    messages = ["\n".join(summary)[:3900]]

    if relevant:
        current = "📰 مهم‌ترین موارد اخیر\n\n"
        for item in relevant[:max_items]:
            block = _item_block(item)
            if len(current) + len(block) + 4 > 3900:
                messages.append(current.rstrip())
                current = "📰 ادامه موارد اخیر\n\n"
            current += block + "\n\n"
        if current.strip():
            messages.append(current.rstrip())
    return messages


def send_messages(client: TelegramClient, chat_id: str | int, messages: list[str]) -> None:
    for message in messages:
        client.send_message(chat_id, message)


def send_run_report(
    run: CollectionRun,
    client: TelegramClient,
    chat_id: str | int,
    max_items: int = 20,
) -> None:
    send_messages(client, chat_id, build_run_report(run, max_items=max_items))
