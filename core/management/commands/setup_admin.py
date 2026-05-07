import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create or update admin user with password from environment variable'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD')

        if not password:
            self.stdout.write(self.style.WARNING('ADMIN_PASSWORD not set, skipping admin setup'))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )

        if not created:
            user.is_staff = True
            user.is_superuser = True

        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Admin user "{username}" created'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Admin user "{username}" password updated'))
