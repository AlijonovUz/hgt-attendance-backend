from django.db import models
from apps.utils.models import BaseModel
from apps.users.models import User


class Notification(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="notifications",
        verbose_name="Foydalanuvchi",
    )
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar matni")
    extra_data = models.JSONField(
        null=True, blank=True, verbose_name="Qo'shimcha ma'lumot"
    )
    is_read = models.BooleanField(default=False, verbose_name="O'qilganmi?")

    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.full_name} - {self.title}"


class UserDevice(BaseModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="devices")
    fcm_token = models.TextField(unique=True)
    device_type = models.CharField(
        max_length=50, choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")]
    )
    device_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.device_type}"
