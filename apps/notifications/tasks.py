import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

from celery import shared_task, group
from firebase_admin import messaging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import UserDevice

logger = logging.getLogger(__name__)

FCM_BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    user_id: str
    title_uz_latn: str
    title_uz_cyrl: str
    title_ru: str
    message_uz_latn: str
    message_uz_cyrl: str
    message_ru: str
    extra_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        missing = [
            f
            for f in ("user_id", "title_uz_latn", "message_uz_latn")
            if not getattr(self, f)
        ]
        if missing:
            raise ValueError(f"Majburiy maydonlar yo'q: {missing}")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data["user_id"],
            title_uz_latn=data.get("title_uz_latn"),
            title_uz_cyrl=data.get("title_uz_cyrl"),
            title_ru=data.get("title_ru"),
            message_uz_latn=data.get("message_uz_latn"),
            message_uz_cyrl=data.get("message_uz_cyrl"),
            message_ru=data.get("message_ru"),
            extra_data=data.get("extra_data") or {},
        )


@shared_task
def mass_notification_sender(raw_list):
    if not raw_list:
        return "Ro'yxat bo'sh"

    valid, skipped = [], 0
    for raw in raw_list:
        try:
            valid.append(
                send_single_notification_task.s(
                    NotificationPayload.from_dict(raw).to_dict()
                )
            )
        except Exception as e:
            logger.warning("Noto'g'ri payload o'tkazib yuborildi: %s | %s", raw, e)
            skipped += 1

    if not valid:
        return "Barcha yozuvlar noto'g'ri."

    group(valid).apply_async()
    return f"{len(valid)} ta yuborildi" + (
        f", {skipped} ta o'tkazib yuborildi." if skipped else "."
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def send_single_notification_task(self, raw):
    try:
        p = NotificationPayload.from_dict(raw)
    except Exception as e:
        raise self.retry(exc=e, max_retries=0)

    group(
        send_websocket_notification.s(raw),
        send_push_notification_task.s(
            p.user_id,
            p.title_uz_latn,
            p.title_uz_cyrl,
            p.title_ru,
            p.message_uz_latn,
            p.message_uz_cyrl,
            p.message_ru,
            p.extra_data,
        ),
        send_telegram_notification_task.s(raw),
    ).apply_async()
    return f"User {p.user_id} uchun tasklar yuborildi."


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def send_websocket_notification(self, data):
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise RuntimeError("Channel layer mavjud emas.")

    async_to_sync(channel_layer.group_send)(
        f"user_{data['user_id']}_notifications",
        {"type": "send_notification", "message": data},
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def send_telegram_notification_task(self, raw):
    from apps.users.models import User
    from django.conf import settings
    from aiogram import Bot
    from aiogram.exceptions import TelegramAPIError
    import asyncio

    if not settings.TELEGRAM_BOT_TOKEN:
        return "Telegram bot token is not configured."

    user_id = raw.get("user_id")
    try:
        user = User.objects.get(id=user_id)
        if not user.telegram_id:
            return "Foydalanuvchi Telegram ga ulanmagan."

        lang = user.language or "uz_latn"

        if lang == "uz_latn":
            title = raw.get("title_uz_latn")
            message = raw.get("message_uz_latn")
        elif lang == "uz_cyrl":
            title = raw.get("title_uz_cyrl")
            message = raw.get("message_uz_cyrl")
        else:
            title = raw.get("title_ru")
            message = raw.get("message_ru")

        full_message = f"🔔 <b>{title}</b>\n\n{message}"

        async def _send():
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            try:
                await bot.send_message(
                    chat_id=user.telegram_id, text=full_message, parse_mode="HTML"
                )
            finally:
                await bot.session.close()

        asyncio.run(_send())
        return f"Telegram orqali yuborildi: {user.id}"
    except User.DoesNotExist:
        return "User not found."
    except Exception as e:
        logger.error(f"Telegram notification error: {e}")
        raise self.retry(exc=e, max_retries=3)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def send_push_notification_task(
    self,
    user_id,
    title_uz_latn,
    title_uz_cyrl,
    title_ru,
    message_uz_latn,
    message_uz_cyrl,
    message_ru,
    extra_data=None,
):
    tokens = list(
        UserDevice.objects.filter(user_id=user_id)
        .exclude(fcm_token__isnull=True)
        .exclude(fcm_token="")
        .values_list("fcm_token", flat=True)
    )

    if not tokens:
        return f"User {user_id} uchun tokenlar yo'q."

    fcm_data = {
        "payload": json.dumps(extra_data or {}),
        "title_uz_latn": title_uz_latn or "",
        "title_uz_cyrl": title_uz_cyrl or "",
        "title_ru": title_ru or "",
        "message_uz_latn": message_uz_latn or "",
        "message_uz_cyrl": message_uz_cyrl or "",
        "message_ru": message_ru or "",
    }
    success = failure = 0
    invalid_tokens = []

    for i in range(0, len(tokens), FCM_BATCH_SIZE):
        batch = tokens[i : i + FCM_BATCH_SIZE]
        response = messaging.send_each_for_multicast(
            messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title_uz_latn or "Xabarnoma",
                    body=message_uz_latn or "",
                ),
                data=fcm_data,
                tokens=batch,
            )
        )
        success += response.success_count
        failure += response.failure_count
        invalid_tokens += [
            batch[j]
            for j, r in enumerate(response.responses)
            if not r.success
            and isinstance(
                r.exception,
                (messaging.UnregisteredError, messaging.SenderIdMismatchError),
            )
        ]

    if invalid_tokens:
        deleted, _ = UserDevice.objects.filter(fcm_token__in=invalid_tokens).delete()
        logger.warning(
            "FCM: %d ta eskirgan token o'chirildi | user=%s", deleted, user_id
        )

    logger.info("FCM: user=%s | ok=%d | fail=%d", user_id, success, failure)
    return f"FCM: {success} muvaffaqiyatli, {failure} muvaffaqiyatsiz"
