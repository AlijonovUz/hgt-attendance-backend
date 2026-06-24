from celery import shared_task
from django.utils import timezone

from apps.users.models import User
from apps.analytics.services import KPIService


@shared_task
def update_kpi_for_user_task(user_id, year, month):
    try:
        user = User.objects.get(id=user_id)
        KPIService.calculate_user_kpi(user, year, month)
    except User.DoesNotExist:
        pass


@shared_task
def recalculate_all_kpis_daily_task():
    now = timezone.localtime()
    users = User.objects.filter(is_active=True, is_fired=False)

    for user in users.iterator(chunk_size=1000):
        update_kpi_for_user_task.delay(user.id, now.year, now.month)


@shared_task
def update_today_attendance_for_user_task(user_id):
    try:
        from apps.analytics.services.daily import DailyKPIService
        user = User.objects.get(id=user_id)
        now_date = timezone.localtime().date()
        DailyKPIService.calculate_daily_snapshot(user, now_date)
    except User.DoesNotExist:
        pass


@shared_task
def recalculate_today_attendance_hourly_task():
    users = User.objects.filter(is_active=True, is_fired=False)
    for user in users.iterator(chunk_size=1000):
        update_today_attendance_for_user_task.delay(user.id)
