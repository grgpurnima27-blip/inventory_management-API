import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

count = User.objects.filter(is_email_verified=False).update(is_email_verified=True)
print(f'Successfully verified {count} users!')