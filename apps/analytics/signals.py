from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.analytics.tasks import update_kpi_for_user_task


@receiver(post_save, sender=Attendance)
def update_kpi_on_attendance(sender, instance, created, **kwargs):
    if created:
        now = timezone.localtime()
        update_kpi_for_user_task.delay(instance.user_id, now.year, now.month)
