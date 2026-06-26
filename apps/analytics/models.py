from django.db import models

from apps.users.models import User
from apps.utils.models import BaseModel


class KPIResult(BaseModel):
    """
    Xodimning har oy yakunidagi KPI hisob-kitoblarini (Reyting, intizom koeffitsienti va 
    ballarini) yig'ib saqlovchi jadval. Maosh tayinlashda shu model asos vazifani bajaradi.
    """
    class RatingCategory(models.TextChoices):
        EXCELLENT = "excellent", "A'lo"
        GOOD = "good", "Yaxshi"
        SATISFACTORY = "satisfactory", "Qoniqarli"
        UNSATISFACTORY = "unsatisfactory", "Qoniqarsiz"

    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="kpi_results", verbose_name="Xodim"
    )
    month = models.DateField(verbose_name="Hisobot oyi")

    total_work_days = models.PositiveIntegerField(
        default=0, verbose_name="Umumiy ish kunlari"
    )
    attended_days = models.PositiveIntegerField(
        default=0, verbose_name="Ishga kelgan kunlari"
    )
    lates_count = models.PositiveIntegerField(
        default=0, verbose_name="Kechikishlar soni"
    )
    left_early_count = models.PositiveIntegerField(
        default=0, verbose_name="Erta ketgan kunlar"
    )

    attendance_kpi = models.FloatField(default=0.0, verbose_name="Davomat KPI (%)")
    monthly_kpi = models.FloatField(default=0.0, verbose_name="Oylik KPI (%)")
    late_coefficient = models.FloatField(
        default=0.0, verbose_name="Kechikish koeffitsienti"
    )
    discipline_coefficient = models.FloatField(
        default=0.0, verbose_name="Intizom koeffitsienti"
    )

    total_score = models.FloatField(default=0.0, verbose_name="Umumiy ball")
    rating_category = models.CharField(
        max_length=20,
        choices=RatingCategory.choices,
        blank=True,
        null=True,
        verbose_name="Reyting",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "KPI Natijasi"
        verbose_name_plural = "KPI Natijalari"
        unique_together = ["user", "month"]

    def __str__(self):
        return f"{self.user.full_name} - {self.month.strftime('%Y-%m')} ({self.get_rating_category_display()})"


class DailyAttendance(BaseModel):
    """
    Xodimning kunlik davomat qisqacha xulosasi (snapshot). Bugun u keldimi, 
    kechikdimi yoki umuman kelmadimi degan aniq faktlar shu jadvalda qayd etiladi.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="daily_attendances",
        verbose_name="Xodim",
    )
    date = models.DateField(verbose_name="Sana")

    schedule_name = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Ish grafigi"
    )
    is_mandatory = models.BooleanField(default=True, verbose_name="Majburiy kunmi?")
    is_holiday = models.BooleanField(default=False, verbose_name="Dam olish kunimi?")

    total_expected = models.PositiveIntegerField(
        default=0, verbose_name="Kutilgan jami"
    )
    present = models.PositiveIntegerField(default=0, verbose_name="Kelgan")
    absent = models.PositiveIntegerField(default=0, verbose_name="Kelmagan")
    late = models.PositiveIntegerField(default=0, verbose_name="Kechikkan")
    left_early = models.PositiveIntegerField(default=0, verbose_name="Erta ketgan")

    class Meta(BaseModel.Meta):
        verbose_name = "Kunlik Davomat"
        verbose_name_plural = "Kunlik Davomatlar"
        unique_together = ["user", "date"]

    def __str__(self):
        return f"{self.user.full_name} - {self.date}"
