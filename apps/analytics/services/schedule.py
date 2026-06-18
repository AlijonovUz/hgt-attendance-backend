import logging
from datetime import time, timedelta
from apps.users.models import Holiday

logger = logging.getLogger(__name__)
class ScheduleHelper:
    @staticmethod
    def get_period_schedule(schedule, start_date, end_date):
        holidays = Holiday.objects.filter(
            start_date__lte=end_date, end_date__gte=start_date
        )
        holiday_dates = set()
        for h in holidays:
            curr = h.start_date
            while curr <= h.end_date:
                holiday_dates.add(curr)
                curr += timedelta(days=1)

        mandatory_weekdays = {0, 1, 2, 3, 4}
        optional_weekdays = set()
        st = time(9, 0, 0)
        et = time(18, 0, 0)
        lst = time(13, 0, 0)
        let = time(14, 0, 0)

        if schedule:
            st = schedule.work_start_time
            et = schedule.work_end_time
            lst = schedule.lunch_start_time
            let = schedule.lunch_end_time
            mandatory_weekdays = set(
                schedule.mandatory_days.values_list("day_number", flat=True)
            )
            optional_weekdays = set(
                schedule.optional_days.values_list("day_number", flat=True)
            )

        schedule_map = {}
        curr = start_date
        while curr <= end_date:
            is_holiday = curr in holiday_dates
            is_mand = (curr.weekday() in mandatory_weekdays) and not is_holiday
            is_opt = (curr.weekday() in optional_weekdays) or is_holiday

            schedule_map[curr] = {
                "is_mandatory": is_mand,
                "is_optional": is_opt,
                "start_time": st,
                "end_time": et,
                "lunch_start": lst,
                "lunch_end": let,
            }
            curr += timedelta(days=1)

        return schedule_map


