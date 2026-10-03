from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="CollectionRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("seen", models.PositiveIntegerField(default=0)),
                ("new", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(blank=True, default=list)),
            ],
            options={"ordering":["-started_at"]},
        ),
        migrations.CreateModel(
            name="Source",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("kind", models.CharField(choices=[("rss","RSS"),("html","HTML")], max_length=20)),
                ("url", models.URLField()),
                ("fallback_url", models.URLField(blank=True)),
                ("enabled", models.BooleanField(default=True)),
                ("last_status", models.CharField(blank=True, max_length=20)),
                ("last_error", models.TextField(blank=True)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Signal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fingerprint", models.CharField(max_length=64, unique=True)),
                ("title", models.TextField()),
                ("url", models.URLField(max_length=1000)),
                ("source", models.CharField(max_length=120)),
                ("published_at", models.CharField(blank=True, max_length=120)),
                ("summary", models.TextField(blank=True)),
                ("drug_name", models.CharField(blank=True, max_length=255)),
                ("category", models.CharField(choices=[("candidate","Candidate"),("review","Review"),("resolved","Resolved"),("foreign","Foreign"),("context","Context")], default="context", max_length=20)),
                ("reason", models.TextField(blank=True)),
                ("review_label", models.CharField(blank=True, choices=[("","Unreviewed"),("confirmed_shortage","Confirmed shortage"),("not_shortage","Not shortage"),("resolved","Resolved"),("uncertain","Uncertain")], max_length=30)),
                ("corrected_drug_name", models.CharField(blank=True, max_length=255)),
                ("note", models.TextField(blank=True)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering":["-first_seen_at"]},
        ),
    ]
