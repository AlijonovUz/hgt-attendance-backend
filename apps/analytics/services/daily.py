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
        schedule_map = ScheduleHelper.get_period_schedule(user.schedule, target_date, target_date)
        day_info = schedule_map.get(target_date)
        if not day_info:
            return None

        start_dt = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        end_time = day_info["end_time"]
        start_time = day_info["start_time"]
        
        shift_end_dt = timezone.make_aware(datetime.combine(target_date, end_time))
        if end_time <= start_time:
            shift_end_dt += timedelta(days=1)
            
        end_dt = shift_end_dt + timedelta(hours=12)

        attendances = Attendance.objects.filter(
            user=user, 
            created_at__gte=start_dt,
            created_at__lte=end_dt
        )
        
        day_atts = []
        for att in attendances:
            loc_time = timezone.localtime(att.created_at)
            if loc_time.date() == target_date:
                day_atts.append(att)
            elif loc_time <= shift_end_dt:
                day_atts.append(att)
            elif att.event_type == Attendance.EventType.CHECK_OUT and loc_time <= end_dt:
                day_atts.append(att)

        is_mand = day_info["is_mandatory"]
        is_opt = day_info["is_optional"]
        schedule_name = user.schedule.name if user.schedule else "Standard"

        check_in = next((a for a in day_atts if a.event_type == Attendance.EventType.CHECK_IN), None)
        check_out = next(
            (a for a in reversed(day_atts) if a.event_type == Attendance.EventType.CHECK_OUT), None
        )

        total_expected = 0
        present = 0
        absent = 0
        late = 0
        left_early = 0
        on_time_in = 0
        on_time_out = 0
        compliant_actions = 0
        
        has_lunch = day_info.get("lunch_start") is not None and day_info.get("lunch_end") is not None
        actions_per_day = 4 if has_lunch else 2
        total_expected_actions = 0

        if is_mand:
            if check_in or check_out or timezone.now() > shift_end_dt:
                total_expected = 1
                total_expected_actions = actions_per_day
        elif check_in or check_out:
            total_expected = 1
            total_expected_actions = actions_per_day

        lunch_start = next((a for a in day_atts if a.event_type == Attendance.EventType.LUNCH_START), None)
        lunch_end = next((a for a in day_atts if a.event_type == Attendance.EventType.LUNCH_END), None)

        if check_in or check_out:
            present = 1

        if check_in:
            check_in_time = timezone.localtime(check_in.created_at).time()
            if check_in_time <= start_time:
                on_time_in = 1
                if is_mand or is_opt:
                    compliant_actions += 1
            else:
                if is_mand:
                    late = 1

        if check_out:
            check_out_time = timezone.localtime(check_out.created_at).time()
            if check_out_time >= end_time:
                on_time_out = 1
                if is_mand or is_opt:
                    compliant_actions += 1
            else:
                if is_mand:
                    left_early = 1

        if not (check_in or check_out) and is_mand:
            if timezone.now() > shift_end_dt:
                absent = 1

        if (is_mand or is_opt) and has_lunch:
            if lunch_start and timezone.localtime(lunch_start.created_at).time() >= day_info["lunch_start"]:
                compliant_actions += 1
            if lunch_end and timezone.localtime(lunch_end.created_at).time() <= day_info["lunch_end"]:
                compliant_actions += 1

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
                "on_time_in": on_time_in,
                "on_time_out": on_time_out,
                "compliant_actions": compliant_actions,
                "total_expected_actions": total_expected_actions
            }
        )
        return snapshot
