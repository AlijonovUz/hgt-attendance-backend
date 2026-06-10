from django.db import models

from apps.users.models import Branch, User
from apps.utils.models import BaseModel


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
    radius = models.PositiveIntegerField(default=10, verbose_name="Radius (metr)")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
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
        User, on_delete=models.CASCADE, related_name="attendances", verbose_name="Xodim"
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
