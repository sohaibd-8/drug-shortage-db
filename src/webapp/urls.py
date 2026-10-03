from django.contrib import admin
from django.urls import path
from monitor.views import dashboard, health, run_collection, send_test_telegram

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("health/", health, name="health"),
    path("collect/", run_collection, name="run_collection"),
    path("telegram/test/", send_test_telegram, name="telegram_test"),
    path("admin/", admin.site.urls),
]
