import calendar
import logging
from datetime import date, timedelta
from django.utils import timezone
from apps.analytics.models import KPIResult

logger = logging.getLogger(__name__)


class KPIService:
    @classmethod
    def calculate_user_kpi(cls, user, year, month):
        start_date = date(year, month, 1)
        _, num_days = calendar.monthrange(year, month)
        end_date = date(year, month, num_days)

        from django.db.models import Sum
        from apps.analytics.models import DailyAttendance
        from apps.analytics.services.daily import DailyKPIService

        today = timezone.localtime().date()
        DailyKPIService.calculate_daily_snapshot(user, today)
        DailyKPIService.calculate_daily_snapshot(user, today - timedelta(days=1))

        stats = DailyAttendance.objects.filter(
            user=user, date__range=(start_date, end_date)
        ).aggregate(
            total_expected=Sum("total_expected"),
            present=Sum("present"),
            absent=Sum("absent"),
            late=Sum("late"),
            left_early=Sum("left_early"),
        )

        total_expected = stats["total_expected"] or 0
        if total_expected == 0:
            return None

        lates_count = stats["late"] or 0
        left_early = stats["left_early"] or 0
        absent = stats["absent"] or 0
        present = stats["present"] or 0

        on_time_in = max(0, present - lates_count)
        on_time_out = max(0, present - left_early)

        compliant_actions = on_time_in + on_time_out
        total_expected_actions = total_expected * 2

        attendance_kpi = (on_time_in / total_expected) * 100
        monthly_kpi = ((on_time_in + on_time_out) / (total_expected * 2)) * 100

        discipline_coefficient = (
            (compliant_actions / total_expected_actions)
            if total_expected_actions > 0
            else 0
        )
        late_coefficient = 1.0
        if total_expected > 0:
            late_ratio = (lates_count + left_early) / total_expected
            if late_ratio > 0:
                late_coefficient = max(0.0, 1.0 - late_ratio)

        total_score = (
            monthly_kpi + attendance_kpi + (discipline_coefficient * 100)
        ) / 3

        if total_score >= 85:
            rating_category = KPIResult.RatingCategory.EXCELLENT
        elif total_score >= 70:
            rating_category = KPIResult.RatingCategory.GOOD
        elif total_score >= 50:
            rating_category = KPIResult.RatingCategory.SATISFACTORY
        else:
            rating_category = KPIResult.RatingCategory.UNSATISFACTORY

        kpi_result, created = KPIResult.objects.update_or_create(
            user=user,
            month=start_date,
            defaults={
                "total_work_days": total_expected,
                "attended_days": present,
                "lates_count": lates_count,
                "left_early_count": left_early,
                "attendance_kpi": round(attendance_kpi, 2),
                "monthly_kpi": round(monthly_kpi, 2),
                "late_coefficient": round(late_coefficient, 2),
                "discipline_coefficient": round(discipline_coefficient, 2),
                "total_score": round(total_score, 2),
                "rating_category": rating_category,
            },
        )
        return kpi_result
