import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class ActionType(models.TextChoices):
        CREATE = "create", "Yaratildi"
        UPDATE = "update", "Yangilandi"
        DELETE = "delete", "O'chirildi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Foydalanuvchi",
    )
    action = models.CharField(
        max_length=20, choices=ActionType.choices, verbose_name="Harakat turi"
    )
    table_name = models.CharField(max_length=100, verbose_name="Jadval (Model) nomi")
    record_id = models.CharField(max_length=255, verbose_name="Yozuv ID")
    object_name = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Obyekt nomi"
    )
    old_values = models.JSONField(null=True, blank=True, verbose_name="Eski qiymatlar")
    new_values = models.JSONField(null=True, blank=True, verbose_name="Yangi qiymatlar")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="IP Manzil"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Audit log"
        verbose_name_plural = "Audit loglar"
        ordering = ["-created_at"]

    def __str__(self):
        user_name = self.user.full_name if self.user else "System"
        return f"{user_name} - {self.get_action_display()} - {self.table_name}"
