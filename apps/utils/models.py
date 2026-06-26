import uuid

from django.db import models


class BaseQuerySet(models.QuerySet):
    """
    Tizimdagi modellarning o'chirilish jarayonini (soft-delete) to'g'ri boshqarish 
    uchun umumiy QuerySet. Asl ma'lumotlarni o'chirmasdan 'is_active=False' holatiga o'tkazadi.
    """
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def delete(self):
        return self.update(is_active=False)

    def hard_delete(self):
        return super().delete()


class BaseModel(models.Model):
    """
    Loyiha davomidagi barcha modellar uchun asosiy va mavhum (abstract) model.
    O'zida ID (UUID), aktivlik holati, yaratilgan va o'zgartirilgan vaqtlarni jamlaydi.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name="Is Active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    objects = BaseQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
