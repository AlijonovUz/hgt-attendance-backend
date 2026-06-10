import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('hgt_attendance')

from celery.schedules import crontab

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'recalculate-all-kpis-every-midnight': {
        'task': 'apps.analytics.tasks.recalculate_all_kpis_daily_task',
        'schedule': crontab(hour=23, minute=55),
    },
}

app.autodiscover_tasks()