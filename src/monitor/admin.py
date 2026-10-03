from django.contrib import admin
from .models import Source, Signal, CollectionRun

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name","kind","enabled","last_status","last_checked_at")
    list_filter = ("enabled","kind","last_status")
    search_fields = ("name","url")

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ("title","source","category","review_label","drug_name","first_seen_at")
    list_filter = ("category","review_label","source")
    search_fields = ("title","drug_name","corrected_drug_name","source")
    readonly_fields = ("fingerprint","first_seen_at","last_seen_at")

@admin.register(CollectionRun)
class CollectionRunAdmin(admin.ModelAdmin):
    list_display = ("started_at","finished_at","seen","new")
    readonly_fields = ("started_at","finished_at","seen","new","errors")
