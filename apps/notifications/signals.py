from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .tasks import mass_notification_sender
from .models import Notification


@receiver(post_save, sender=Notification)
def post_save_handler(sender, instance, created, **kwargs):
    if created:
        message_data = {
            "user_id": instance.user.id,
            "id": instance.id,
            "title_uz_latn": instance.title_uz_latn,
            "title_uz_cyrl": instance.title_uz_cyrl,
            "title_ru": instance.title_ru,
            "message_uz_latn": instance.message_uz_latn,
            "message_uz_cyrl": instance.message_uz_cyrl,
            "message_ru": instance.message_ru,
            "extra_data": instance.extra_data,
            "created_at": instance.created_at.isoformat(),
        }

        transaction.on_commit(lambda: mass_notification_sender.delay([message_data]))
