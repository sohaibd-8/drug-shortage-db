import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Ensure an admin user exists from ADMIN_* or DJANGO_SUPERUSER_* environment variables."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME") or os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("ADMIN_PASSWORD") or os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = os.getenv("ADMIN_EMAIL") or os.getenv("DJANGO_SUPERUSER_EMAIL") or ""

        if not username or not password:
            self.stdout.write(self.style.WARNING("Admin bootstrap skipped: username/password not configured"))
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Admin user {action}: {username}"))
