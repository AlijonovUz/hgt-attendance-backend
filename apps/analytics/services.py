import calendar
from datetime import date, datetime, time

from django.utils import timezone

from apps.attendance.models import Attendance
from apps.analytics.models import KPIResult


def get_work_days(year, month):
    today = timezone.localtime().date()
    _, num_days = calendar.monthrange(year, month)

    work_days = 0
    for day in range(1, num_days + 1):
        d = date(year, month, day)
        if d > today:
            break
        if d.weekday() != 6:
            work_days += 1

    return work_days


def calculate_user_kpi(user, year, month):
    work_days = get_work_days(year, month)
    if work_days == 0:
        return None

    start_date = timezone.make_aware(datetime(year, month, 1))
    _, num_days = calendar.monthrange(year, month)
    end_date = timezone.make_aware(datetime(year, month, num_days, 23, 59, 59))

    attendances = Attendance.objects.filter(
        user=user, created_at__range=(start_date, end_date)
    )

    days_arrived_on_time = 0
    days_left_on_time = 0
    lates_count = 0
    compliant_actions = 0

    grouped = {}
    for att in attendances:
        d = timezone.localtime(att.created_at).date()
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(att)

    for d, atts in grouped.items():
        check_ins = [a for a in atts if a.event_type == Attendance.EventType.CHECK_IN]
        if check_ins:
            first_in = min([timezone.localtime(a.created_at).time() for a in check_ins])
            if first_in <= time(9, 0, 0):
                days_arrived_on_time += 1
                compliant_actions += 1
            else:
                lates_count += 1

        lunch_starts = [
            a for a in atts if a.event_type == Attendance.EventType.LUNCH_START
        ]
        if lunch_starts:
            first_lunch_start = min(
                [timezone.localtime(a.created_at).time() for a in lunch_starts]
            )
            if first_lunch_start >= time(13, 0, 0):
                compliant_actions += 1

        lunch_ends = [a for a in atts if a.event_type == Attendance.EventType.LUNCH_END]
        if lunch_ends:
            first_lunch_end = min(
                [timezone.localtime(a.created_at).time() for a in lunch_ends]
            )
            if first_lunch_end <= time(14, 0, 0):
                compliant_actions += 1

        check_outs = [a for a in atts if a.event_type == Attendance.EventType.CHECK_OUT]
        if check_outs:
            last_out = max([timezone.localtime(a.created_at).time() for a in check_outs])
            if last_out >= time(18, 0, 0):
                days_left_on_time += 1
                compliant_actions += 1

    total_expected_actions = work_days * 4

    attendance_kpi = (days_arrived_on_time / work_days * 100) if work_days > 0 else 0

    monthly_kpi = (
        ((days_arrived_on_time + days_left_on_time) / (work_days * 2)) * 100
        if work_days > 0
        else 0
    )

    late_coefficient = lates_count / work_days if work_days > 0 else 0

    discipline_coefficient = (
        (compliant_actions / total_expected_actions) if total_expected_actions > 0 else 0
    )

    attendance_percentage = (len(grouped) / work_days * 100) if work_days > 0 else 0

    total_score = (monthly_kpi + attendance_percentage + (discipline_coefficient * 100)) / 3
    total_score = round(total_score, 2)

    if total_score >= 90:
        rating_category = KPIResult.RatingCategory.EXCELLENT
    elif total_score >= 80:
        rating_category = KPIResult.RatingCategory.GOOD
    elif total_score >= 70:
        rating_category = KPIResult.RatingCategory.SATISFACTORY
    else:
        rating_category = KPIResult.RatingCategory.UNSATISFACTORY

    kpi_result, _ = KPIResult.objects.update_or_create(
        user=user,
        month=date(year, month, 1),
        defaults={
            "total_work_days": work_days,
            "days_arrived_on_time": days_arrived_on_time,
            "days_left_on_time": days_left_on_time,
            "lates_count": lates_count,
            "total_actions_expected": total_expected_actions,
            "compliant_actions": compliant_actions,
            "attendance_kpi": round(attendance_kpi, 2),
            "monthly_kpi": round(monthly_kpi, 2),
            "late_coefficient": round(late_coefficient, 2),
            "discipline_coefficient": round(discipline_coefficient, 2),
            "total_score": total_score,
            "rating_category": rating_category,
        },
    )

    return kpi_result
