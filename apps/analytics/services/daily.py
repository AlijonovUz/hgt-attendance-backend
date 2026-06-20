import logging
from datetime import date, datetime, timedelta
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.analytics.models import DailyAttendance
from apps.analytics.services import ScheduleHelper

logger = logging.getLogger(__name__)


class DailyKPIService:
    @classmethod
    def calculate_daily_snapshot(cls, user, target_date: date):
        schedule_map = ScheduleHelper.get_period_schedule(
            user.schedule, target_date, target_date
        )
        day_info = schedule_map.get(target_date)
        if not day_info:
            return None

        end_time = day_info["end_time"]
        start_time = day_info["start_time"]

        shift_start_dt = timezone.make_aware(datetime.combine(target_date, start_time))
        shift_end_dt = timezone.make_aware(datetime.combine(target_date, end_time))
        if end_time <= start_time:
            shift_end_dt += timedelta(days=1)

        start_dt = shift_start_dt - timedelta(hours=6)
        end_dt = shift_end_dt + timedelta(hours=12)

        attendances = Attendance.objects.filter(
            user=user, created_at__gte=start_dt, created_at__lte=end_dt
        )

        day_atts = []
        for att in attendances:
            loc_time = timezone.localtime(att.created_at)
            if loc_time.date() == target_date:
                day_atts.append(att)
            elif loc_time <= shift_end_dt:
                day_atts.append(att)
            elif (
                att.event_type == Attendance.EventType.CHECK_OUT and loc_time <= end_dt
            ):
                day_atts.append(att)

        if not day_atts and target_date < user.date_joined.date():
            DailyAttendance.objects.filter(user=user, date=target_date).delete()
            return None

        is_mand = day_info["is_mandatory"]
        is_opt = day_info["is_optional"]
        schedule_name = user.schedule.name if user.schedule else "Standard"

        check_in = next(
            (a for a in day_atts if a.event_type == Attendance.EventType.CHECK_IN), None
        )
        check_out = next(
            (
                a
                for a in reversed(day_atts)
                if a.event_type == Attendance.EventType.CHECK_OUT
            ),
            None,
        )

        total_expected = 0
        present = 0
        absent = 0
        late = 0
        left_early = 0
        has_lunch = (
            day_info.get("lunch_start") is not None
            and day_info.get("lunch_end") is not None
        )
        actions_per_day = 4 if has_lunch else 2

        if is_mand:
            if check_in or check_out or timezone.now() > shift_end_dt:
                total_expected = 1
        elif check_in or check_out:
            total_expected = 1

        lunch_start = next(
            (a for a in day_atts if a.event_type == Attendance.EventType.LUNCH_START),
            None,
        )
        lunch_end = next(
            (a for a in day_atts if a.event_type == Attendance.EventType.LUNCH_END),
            None,
        )

        if check_in or check_out:
            present = 1

        if check_in:
            check_in_dt = timezone.localtime(check_in.created_at)
            if check_in_dt > shift_start_dt:
                if is_mand:
                    late = 1

        if check_out:
            check_out_dt = timezone.localtime(check_out.created_at)
            if check_out_dt < shift_end_dt:
                if is_mand:
                    left_early = 1
        elif present and is_mand and timezone.now() > shift_end_dt:
            left_early = 1

        if not (check_in or check_out) and is_mand:
            if timezone.now() > shift_end_dt:
                absent = 1

        snapshot, _ = DailyAttendance.objects.update_or_create(
            user=user,
            date=target_date,
            defaults={
                "schedule_name": schedule_name,
                "is_mandatory": is_mand,
                "is_holiday": day_info.get("is_optional", False) and not is_mand,
                "total_expected": total_expected,
                "present": present,
                "absent": absent,
                "late": late,
                "left_early": left_early,
            },
        )
        return snapshot
