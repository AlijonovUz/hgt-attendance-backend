import uuid
from datetime import time

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.utils.models import BaseModel
from apps.utils.validators import phone_validator, FileSizeValidator

from .managers import UserManager


class Permission(BaseModel):
    """
    Tizimdagi individual huquqlarni (masalan, 'kpi_view_all') saqlovchi model.
    """
    name = models.CharField(max_length=255, verbose_name="Ruxsat nomi")
    code = models.CharField(max_length=100, unique=True, verbose_name="Ruxsat kodi")

    class Meta(BaseModel.Meta):
        verbose_name = "Ruxsat (Permission)"
        verbose_name_plural = "Ruxsatlar"

    def __str__(self):
        return self.name


class Role(BaseModel):
    """
    Tizim Rollari (Admin, Xodim) ni ifodalovchi model.
    Rolga tegishli Permission larni o'z ichiga oladi.
    """
    name = models.CharField(max_length=255, unique=True, verbose_name="Rol nomi")
    permissions = models.ManyToManyField(
        Permission, blank=True, verbose_name="Ruxsatlar"
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Rol"
        verbose_name_plural = "Rollar"

    def __str__(self):
        return self.name


class Region(BaseModel):
    """Viloyatlar ro'yxatini saqlovchi model (Masalan: Toshkent shahar, Samarqand)."""
    name = models.CharField(max_length=255, verbose_name="Viloyat nomi")

    class Meta(BaseModel.Meta):
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"

    def __str__(self):
        return self.name


class District(BaseModel):
    """Viloyatga qarashli tumanlarni saqlovchi model."""
    name = models.CharField(max_length=255, verbose_name="Tuman nomi")
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="districts",
        verbose_name="Viloyat",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"

    def __str__(self):
        return self.name


class Branch(BaseModel):
    """
    Tashkilotning xususiy filiallarini (ish joylarini) saqlovchi model.
    Xodimlar filialga qarab guruhlanadi.
    """
    name = models.CharField(max_length=255, verbose_name="Filial nomi")
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="branches",
        verbose_name="Viloyat",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="branches",
        verbose_name="Tuman",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"

    def __str__(self):
        return self.name


class Department(BaseModel):
    """Har bir filial ichidagi kichik bo'limlar (Kassa, HR, IT)."""
    name = models.CharField(max_length=255, verbose_name="Bo'lim nomi")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="departments",
        verbose_name="Filial",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"

    def __str__(self):
        return self.name


class Position(BaseModel):
    """Xodimlarning tashkilotdagi rasmiy ish lavozimlari ro'yxati."""
    name = models.CharField(max_length=255, verbose_name="Lavozim nomi")
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="positions",
        verbose_name="Bo'lim",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Lavozim"
        verbose_name_plural = "Lavozimlar"

    def __str__(self):
        return self.name


class WeekDay(BaseModel):
    """Haftaning 7 kunini ko'rsatuvchi ma'lumotnoma (Reference) modeli."""
    name = models.CharField(max_length=50, verbose_name="Hafta kuni")
    day_number = models.IntegerField(unique=True, verbose_name="Raqami (0-6)")

    class Meta(BaseModel.Meta):
        verbose_name = "Hafta kuni"
        verbose_name_plural = "Hafta kunlari"
        ordering = ["day_number"]

    def __str__(self):
        return self.name


class Holiday(BaseModel):
    """Davlat miqyosidagi yoki ichki dam olish kunlari (bayramlar)."""
    title = models.CharField(max_length=255, verbose_name="Bayram nomi")
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    end_date = models.DateField(verbose_name="Tugash sanasi")

    class Meta(BaseModel.Meta):
        verbose_name = "Bayram / Qizil sana"
        verbose_name_plural = "Bayramlar"
        ordering = ["start_date"]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                {"start_date": "Boshlanish sanasi tugash sanasidan katta bo'lishi mumkin emas."}
            )

    def __str__(self):
        return self.title


class WorkSchedule(BaseModel):
    """
    Ish grafiki jadvallari. Bunga ko'ra qaysi soatda ish boshlanishi, tushlik vaqti
    va qaysi kunlari ish majburiy/ixtiyoriyligi belgilanadi.
    """
    name = models.CharField(max_length=255, verbose_name="Jadval nomi")
    work_start_time = models.TimeField(
        default=time(9, 0), verbose_name="Ish boshlanishi"
    )
    work_end_time = models.TimeField(default=time(18, 0), verbose_name="Ish tugashi")
    lunch_start_time = models.TimeField(
        null=True, blank=True, verbose_name="Tushlik boshlanishi"
    )
    lunch_end_time = models.TimeField(
        null=True, blank=True, verbose_name="Tushlik tugashi"
    )

    mandatory_days = models.ManyToManyField(
        WeekDay, related_name="mandatory_schedules", verbose_name="Majburiy kunlar"
    )
    optional_days = models.ManyToManyField(
        WeekDay,
        related_name="optional_schedules",
        blank=True,
        verbose_name="Ixtiyoriy kunlar",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Ish grafigi"
        verbose_name_plural = "Ish grafiklari"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Tizimdagi asosiy foydalanuvchi va xodim modeli. 
    Ushbu model o'zida Face ID, Telegram ID va Ishga tegishli barcha holatlarni saqlaydi.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=255, unique=True, verbose_name="F.I.Sh")
    jshshir = models.CharField(
        max_length=14, unique=True, null=True, blank=True, verbose_name="JShShIR"
    )
    phone = models.CharField(
        max_length=13,
        unique=True,
        null=True,
        blank=True,
        validators=[phone_validator],
        verbose_name="Telefon",
    )
    face_image = models.ImageField(
        upload_to="faces/",
        null=True,
        blank=True,
        validators=[FileSizeValidator(max_size_mb=5)],
        verbose_name="Face ID rasm",
    )

    telegram_id = models.BigIntegerField(
        unique=True, null=True, blank=True, verbose_name="Telegram ID"
    )
    language = models.CharField(
        max_length=10,
        choices=[
            ("uz_latn", "Uzbek (Lotin)"),
            ("uz_cyrl", "Ўзбек (Кирил)"),
            ("ru", "Русский"),
        ],
        default="uz_latn",
        verbose_name="Tizim Tili",
    )

    is_fired = models.BooleanField(default=False, verbose_name="Bo'shatilgan")
    fired_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Bo'shatilgan sana"
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Filial",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Bo'lim",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Lavozim",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Rol",
    )
    schedule = models.ForeignKey(
        WorkSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Ish grafigi",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")
    is_password_changed = models.BooleanField(
        default=False, verbose_name="Parol o'zgartirilganmi?"
    )

    username = None
    USERNAME_FIELD = "full_name"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ["-created_at"]

    def has_permission(self, perm_code):
        if self.is_superuser:
            return True

        if self.role:
            return self.role.permissions.filter(code=perm_code).exists()
        return False

    def has_any_permission(self, perm_codes):
        if self.is_superuser:
            return True

        if self.role:
            return self.role.permissions.filter(code__in=perm_codes).exists()
        return False

    def has_role(self, role_names):
        if self.is_superuser:
            return True

        if not self.role:
            return False

        if isinstance(role_names, str):
            return self.role.name == role_names

        return self.role.name in role_names

    def __str__(self):
        return self.full_name
