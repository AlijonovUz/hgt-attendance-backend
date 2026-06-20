import logging
from collections import defaultdict
from django.utils import timezone
from django.db.models import Sum

from apps.attendance.models import Attendance
from apps.analytics.models import DailyAttendance

logger = logging.getLogger(__name__)


class AttendanceService:
    @staticmethod
    def get_personal_stats(user, year: int, month: int) -> dict:
        stats = DailyAttendance.objects.filter(
            user=user, date__year=year, date__month=month
        ).aggregate(
            present=Sum("present"),
            late=Sum("late"),
        )
        present_days = stats["present"] or 0
        late_days = stats["late"] or 0

        attendances = Attendance.objects.filter(
            user=user, created_at__year=year, created_at__month=month
        ).order_by("created_at")

        daily_logs = defaultdict(list)
        for att in attendances:
            loc_time = timezone.localtime(att.created_at)
            daily_logs[loc_time.date()].append(att)

        total_worked_seconds = 0
        check_in_seconds_sum = 0
        check_in_count = 0

        for date_val, logs in daily_logs.items():
            check_ins = [
                log for log in logs if log.event_type == Attendance.EventType.CHECK_IN
            ]
            check_outs = [
                log for log in logs if log.event_type == Attendance.EventType.CHECK_OUT
            ]

            if check_ins:
                first_check_in = check_ins[0]
                first_dt = timezone.localtime(first_check_in.created_at)
                secs = first_dt.hour * 3600 + first_dt.minute * 60 + first_dt.second
                check_in_seconds_sum += secs
                check_in_count += 1

                if check_outs:
                    last_check_out = check_outs[-1]
                    last_dt = timezone.localtime(last_check_out.created_at)
                    worked_secs = (last_dt - first_dt).total_seconds()

                    lunch_starts = [
                        log
                        for log in logs
                        if log.event_type == Attendance.EventType.LUNCH_START
                    ]
                    lunch_ends = [
                        log
                        for log in logs
                        if log.event_type == Attendance.EventType.LUNCH_END
                    ]
                    if lunch_starts and lunch_ends:
                        l_start = timezone.localtime(lunch_starts[-1].created_at)
                        l_end = timezone.localtime(lunch_ends[-1].created_at)
                        if l_end > l_start:
                            worked_secs -= (l_end - l_start).total_seconds()

                    if worked_secs > 0:
                        total_worked_seconds += worked_secs

        avg_check_in = "00:00"
        if check_in_count > 0:
            avg_sec = int(check_in_seconds_sum / check_in_count)
            avg_h = avg_sec // 3600
            avg_m = (avg_sec % 3600) // 60
            avg_check_in = f"{avg_h:02d}:{avg_m:02d}"

        total_worked_hours = int(total_worked_seconds // 3600)

        return {
            "present_days": present_days,
            "late_days": late_days,
            "avg_check_in": avg_check_in,
            "total_worked_hours": total_worked_hours,
        }
