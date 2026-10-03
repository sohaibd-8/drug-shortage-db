from django.db import models

class Source(models.Model):
    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=20, choices=[("rss","RSS"),("html","HTML")])
    url = models.URLField()
    fallback_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    last_status = models.CharField(max_length=20, blank=True)
    last_error = models.TextField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Signal(models.Model):
    CATEGORY_CHOICES = [
        ("candidate","Candidate"),
        ("review","Review"),
        ("resolved","Resolved"),
        ("foreign","Foreign"),
        ("context","Context"),
    ]
    REVIEW_CHOICES = [
        ("","Unreviewed"),
        ("confirmed_shortage","Confirmed shortage"),
        ("not_shortage","Not shortage"),
        ("resolved","Resolved"),
        ("uncertain","Uncertain"),
    ]
    fingerprint = models.CharField(max_length=64, unique=True)
    title = models.TextField()
    url = models.URLField(max_length=1000)
    source = models.CharField(max_length=120)
    published_at = models.CharField(max_length=120, blank=True)
    summary = models.TextField(blank=True)
    drug_name = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="context")
    reason = models.TextField(blank=True)
    review_label = models.CharField(max_length=30, choices=REVIEW_CHOICES, blank=True)
    corrected_drug_name = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-first_seen_at"]

    def __str__(self):
        return self.title[:100]

class CollectionRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    seen = models.PositiveIntegerField(default=0)
    new = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at"]
