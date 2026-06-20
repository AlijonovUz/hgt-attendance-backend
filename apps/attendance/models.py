from django.db import models

from apps.users.models import Branch, User
from apps.utils.models import BaseModel


from django.core.validators import MinValueValidator, MaxValueValidator


class Geozone(BaseModel):
    class ZoneType(models.TextChoices):
        MAIN_OFFICE = "main_office", "Markaziy apparat"
        REGION_BRANCH = "region_branch", "Viloyat filiali"
        DISTRICT_BRANCH = "district_branch", "Tuman bo'limi"
        SPECIAL_OBJECT = "special_object", "Maxsus obyekt"
        TEMP_OBJECT = "temp_object", "Vaqtinchalik obyekt"

    name = models.CharField(max_length=255, verbose_name="Geozona nomi")
    zone_type = models.CharField(
        max_length=50,
        choices=ZoneType.choices,
        default=ZoneType.MAIN_OFFICE,
        verbose_name="Geozona turi",
    )
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, verbose_name="Kenglik (Latitude)"
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, verbose_name="Uzunlik (Longitude)"
    )
    radius = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(50), MaxValueValidator(500)],
        verbose_name="Radius (metr)",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="geozones",
        verbose_name="Filial",
        null=True,
        blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Geozona"
        verbose_name_plural = "Geozonalar"

    def __str__(self):
        return f"{self.name} ({self.radius}m)"


class Attendance(BaseModel):
    class EventType(models.TextChoices):
        CHECK_IN = "check_in", "Kelish"
        LUNCH_START = "lunch_start", "Tushlikka chiqish"
        LUNCH_END = "lunch_end", "Tushlikdan qaytish"
        CHECK_OUT = "check_out", "Ketish"

    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="attendances", verbose_name="Xodim"
    )
    event_type = models.CharField(
        max_length=50, choices=EventType.choices, verbose_name="Hodisa turi"
    )
    gps_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name="Kenglik (Latitude)",
        null=True,
        blank=True,
    )
    gps_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name="Uzunlik (Longitude)",
        null=True,
        blank=True,
    )
    face_verify = models.BooleanField(default=False, verbose_name="Face ID tasdiqlandi")

    class Meta(BaseModel.Meta):
        verbose_name = "Davomat hodisasi"
        verbose_name_plural = "Davomat hodisalari"

    def __str__(self):
        return f"{self.user.full_name} - {self.get_event_type_display()}"


class FaceLog(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="face_logs", verbose_name="Xodim"
    )
    is_success = models.BooleanField(default=False, verbose_name="Muvaffaqiyatli")
    distance = models.FloatField(
        null=True, blank=True, verbose_name="Solishtirish masofasi"
    )
    message = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Xabar"
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Face ID Logi"
        verbose_name_plural = "Face ID Loglari"

    def __str__(self):
        return (
            f"{self.user.full_name} - {'Muvaffaqiyatli' if self.is_success else 'Xato'}"
        )


class GpsLog(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="gps_logs", verbose_name="Xodim"
    )
    geozone = models.ForeignKey(
        Geozone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gps_logs",
        verbose_name="Geozona",
    )
    is_success = models.BooleanField(default=False, verbose_name="Muvaffaqiyatli")
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, verbose_name="Kenglik (Latitude)"
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, verbose_name="Uzunlik (Longitude)"
    )
    distance_meters = models.FloatField(
        null=True, blank=True, verbose_name="Masofa (metr)"
    )
    message = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Xabar"
    )

    class Meta(BaseModel.Meta):
        verbose_name = "GPS Logi"
        verbose_name_plural = "GPS Loglari"

    def __str__(self):
        return (
            f"{self.user.full_name} - {'Ichida' if self.is_success else 'Tashqarida'}"
        )


class SignatureLog(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="signature_logs",
        verbose_name="Xodim",
    )
    is_valid = models.BooleanField(default=False, verbose_name="Muvaffaqiyatli")
    provided_time = models.DateTimeField(
        null=True, blank=True, verbose_name="Yuborilgan vaqt"
    )
    message = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Xabar"
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Imzo Logi"
        verbose_name_plural = "Imzo Loglari"

    def __str__(self):
        return (
            f"{self.user.full_name} - {'Muvaffaqiyatli' if self.is_valid else 'Xato'}"
        )
