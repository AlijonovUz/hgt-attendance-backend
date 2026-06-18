import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import User
from apps.analytics.services.daily import DailyKPIService

user = User.objects.get(full_name__icontains='Abdulbosit')
today = timezone.localtime().date()

from datetime import timedelta
DailyKPIService.calculate_daily_snapshot(user, today - timedelta(days=1))
DailyKPIService.calculate_daily_snapshot(user, today)
print("Updated!")
