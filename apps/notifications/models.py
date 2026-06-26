from django.db import models
from apps.utils.models import BaseModel
from apps.users.models import User


class Notification(BaseModel):
    """
    Tizim bo'ylab foydalanuvchiga yuborilgan barcha bildirishnomalarni (Kechikdingiz, 
    Erta ketdingiz kabi) 3 xil tilda saqlovchi model.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="notifications",
        verbose_name="Foydalanuvchi",
    )
    title_uz_latn = models.CharField(
        max_length=255, verbose_name="Sarlavha (Lotin)", null=True, blank=True
    )
    title_uz_cyrl = models.CharField(
        max_length=255, verbose_name="Sarlavha (Krill)", null=True, blank=True
    )
    title_ru = models.CharField(
        max_length=255, verbose_name="Sarlavha (Rus)", null=True, blank=True
    )
    message_uz_latn = models.TextField(
        verbose_name="Xabar matni (Lotin)", null=True, blank=True
    )
    message_uz_cyrl = models.TextField(
        verbose_name="Xabar matni (Krill)", null=True, blank=True
    )
    message_ru = models.TextField(
        verbose_name="Xabar matni (Rus)", null=True, blank=True
    )
    extra_data = models.JSONField(
        null=True, blank=True, verbose_name="Qo'shimcha ma'lumot"
    )
    is_read = models.BooleanField(default=False, verbose_name="O'qilganmi?")

    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ["-created_at"]

    def __str__(self):
        title = self.title_uz_latn or self.title_ru or self.title_uz_cyrl or "Xabarnoma"
        return f"{self.user.full_name} - {title}"


class UserDevice(BaseModel):
    """
    Foydalanuvchining mobil qurilmasi ma'lumotlari (FCM Token, OS) ni saqlovchi model.
    Pusn Notification yuborishda faqat tizimga kirgan va saqlangan qurilmalarga jo'natiladi.
    """
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="devices")
    fcm_token = models.TextField(unique=True)
    device_type = models.CharField(
        max_length=50, choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")]
    )
    device_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.device_type}"
