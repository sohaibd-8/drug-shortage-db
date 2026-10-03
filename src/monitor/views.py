import os
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from .models import Signal, Source, CollectionRun
from .services import collect_now
from iran_shortages.telegram import TelegramClient, TelegramError

def health(request):
    return JsonResponse({"ok": True})

@staff_member_required
def dashboard(request):
    context = {
        "signals": Signal.objects.count(),
        "candidates": Signal.objects.filter(category__in=["candidate","review"]).count(),
        "confirmed": Signal.objects.filter(review_label="confirmed_shortage").count(),
        "sources": Source.objects.count(),
        "latest_signals": Signal.objects.all()[:10],
        "latest_run": CollectionRun.objects.first(),
    }
    return render(request, "monitor/dashboard.html", context)

@staff_member_required
def run_collection(request):
    if request.method == "POST":
        run = collect_now()
        messages.success(request, f"جمع‌آوری انجام شد: {run.seen} مورد، {run.new} مورد جدید")
    return redirect("dashboard")

@staff_member_required
def send_test_telegram(request):
    if request.method == "POST":
        try:
            TelegramClient(os.getenv("TELEGRAM_BOT_TOKEN","")).send_message(
                os.getenv("TELEGRAM_CHAT_ID",""),
                "✅ اتصال ربات پایش کمبود دارو با موفقیت برقرار است."
            )
            messages.success(request, "پیام تست تلگرام ارسال شد.")
        except TelegramError as exc:
            messages.error(request, f"خطای تلگرام: {exc}")
    return redirect("dashboard")
