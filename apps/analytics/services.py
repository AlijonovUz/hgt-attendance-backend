import logging
import calendar
from datetime import date, datetime, time, timedelta
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.analytics.models import KPIResult
from apps.users.models import User, Branch, Holiday

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


class KPIService:
    @classmethod
    def calculate_user_kpi(cls, user, year, month):
        start_date = date(year, month, 1)
        _, num_days = calendar.monthrange(year, month)
        end_date = date(year, month, num_days)
        today = timezone.localtime().date()
        user_start_date = timezone.localtime(user.created_at).date()
        user_end_date = (
            timezone.localtime(user.fired_at).date()
            if user.is_fired and user.fired_at
            else today
        )

        actual_start_date = max(start_date, user_start_date)
        actual_end_date = min(end_date, today, user_end_date)

        if actual_start_date > actual_end_date:
            return None

        schedule_map = ScheduleHelper.get_period_schedule(
            user.schedule, actual_start_date, actual_end_date
        )

        work_days = sum(1 for d, info in schedule_map.items() if info["is_mandatory"])
        if work_days == 0:
            return None

        start_dt = timezone.make_aware(
            datetime(start_date.year, start_date.month, start_date.day)
        )
        end_dt = timezone.make_aware(
            datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        )

        attendances = Attendance.objects.filter(
            user=user, created_at__range=(start_dt, end_dt)
        )

        days_arrived_on_time = 0
        days_left_on_time = 0
        lates_count = 0
        compliant_actions = 0
        bonus_actions = 0

        grouped = {}
        for att in attendances:
            d = timezone.localtime(att.created_at).date()
            if d not in grouped:
                grouped[d] = []
            grouped[d].append(att)

        for d, atts in grouped.items():
            if d not in schedule_map:
                continue
            info = schedule_map[d]
            is_mand = info["is_mandatory"]
            is_opt = info["is_optional"]

            if not is_mand and not is_opt:
                is_opt = True

            check_ins = [
                a for a in atts if a.event_type == Attendance.EventType.CHECK_IN
            ]
            if check_ins:
                first_in = min(
                    [timezone.localtime(a.created_at).time() for a in check_ins]
                )
                if first_in <= info["start_time"]:
                    if is_mand:
                        days_arrived_on_time += 1
                        compliant_actions += 1
                    elif is_opt:
                        bonus_actions += 1
                else:
                    if is_mand:
                        lates_count += 1

            lunch_starts = [
                a for a in atts if a.event_type == Attendance.EventType.LUNCH_START
            ]
            if lunch_starts and info.get("lunch_start") is not None:
                first_lunch_start = min(
                    [timezone.localtime(a.created_at).time() for a in lunch_starts]
                )
                if first_lunch_start >= info["lunch_start"]:
                    if is_mand:
                        compliant_actions += 1
                    elif is_opt:
                        bonus_actions += 1

            lunch_ends = [
                a for a in atts if a.event_type == Attendance.EventType.LUNCH_END
            ]
            if lunch_ends and info.get("lunch_end") is not None:
                first_lunch_end = min(
                    [timezone.localtime(a.created_at).time() for a in lunch_ends]
                )
                if first_lunch_end <= info["lunch_end"]:
                    if is_mand:
                        compliant_actions += 1
                    elif is_opt:
                        bonus_actions += 1

            check_outs = [
                a for a in atts if a.event_type == Attendance.EventType.CHECK_OUT
            ]
            if check_outs:
                last_out = max(
                    [timezone.localtime(a.created_at).time() for a in check_outs]
                )
                if last_out >= info["end_time"]:
                    if is_mand:
                        days_left_on_time += 1
                        compliant_actions += 1
                    elif is_opt:
                        bonus_actions += 1

        has_lunch = (
            user.schedule
            and user.schedule.lunch_start_time
            and user.schedule.lunch_end_time
        )
        actions_per_day = 4 if has_lunch else 2
        total_expected_actions = work_days * actions_per_day

        attendance_kpi = (
            (days_arrived_on_time / work_days * 100) if work_days > 0 else 0
        )
        monthly_kpi = (
            ((days_arrived_on_time + days_left_on_time) / (work_days * 2) * 100)
            if work_days > 0
            else 0
        )
        late_coefficient = lates_count / work_days if work_days > 0 else 0

        discipline_coefficient = (
            (compliant_actions / total_expected_actions)
            if total_expected_actions > 0
            else 0
        )

        total_score = (
            monthly_kpi + attendance_kpi + (discipline_coefficient * 100)
        ) / 3
        total_score = round(total_score, 2)

        attended_days = len(grouped.keys())

        if total_score >= 90:
            rating_category = KPIResult.RatingCategory.EXCELLENT
        elif total_score >= 80:
            rating_category = KPIResult.RatingCategory.GOOD
        elif total_score >= 70:
            rating_category = KPIResult.RatingCategory.SATISFACTORY
        else:
            rating_category = KPIResult.RatingCategory.UNSATISFACTORY

        kpi_result, created = KPIResult.objects.update_or_create(
            user=user,
            month=date(year, month, 1),
            defaults={
                "total_work_days": work_days,
                "attended_days": attended_days,
                "days_arrived_on_time": days_arrived_on_time,
                "days_left_on_time": days_left_on_time,
                "lates_count": lates_count,
                "attendance_kpi": round(attendance_kpi, 2),
                "monthly_kpi": round(monthly_kpi, 2),
                "late_coefficient": round(late_coefficient, 2),
                "discipline_coefficient": round(discipline_coefficient, 2),
                "total_score": total_score,
                "rating_category": rating_category,
            },
        )
        return kpi_result


class DashboardService:
    @staticmethod
    def get_dashboard_stats(
        user,
        start_date=None,
        end_date=None,
        region_id=None,
        district_id=None,
        branch_id=None,
        widgets=None,
    ):
        if widgets is None:
            widgets = ["summary", "weekly_dynamics", "today_status", "branch_ratings"]

        today_date = timezone.localtime().date()
        if start_date is None or end_date is None:
            start_date = today_date
            end_date = today_date

        period_days = (end_date - start_date).days + 1
        prev_start_date = start_date - timedelta(days=period_days)
        prev_end_date = start_date - timedelta(days=1)
        first_day_of_month = end_date.replace(day=1)

        base_users = (
            User.objects.all()
            .select_related("schedule", "branch")
            .prefetch_related("schedule__mandatory_days", "schedule__optional_days")
        )

        if not (user.is_superuser or user.has_permission("analytics_view_all")):
            if (
                user.has_permission("analytics_view_region")
                and user.branch
                and user.branch.region
            ):
                base_users = base_users.filter(branch__region=user.branch.region)
            elif (
                user.has_permission("analytics_view_district")
                and user.branch
                and user.branch.district
            ):
                base_users = base_users.filter(branch__district=user.branch.district)
            elif user.has_permission("analytics_view_branch") and user.branch:
                base_users = base_users.filter(branch=user.branch)
            elif user.has_permission("analytics_view_dept") and user.department:
                base_users = base_users.filter(department=user.department)
            else:
                base_users = base_users.filter(id=user.id)

        if region_id:
            base_users = base_users.filter(branch__region_id=region_id)
        if district_id:
            base_users = base_users.filter(branch__district_id=district_id)
        if branch_id:
            base_users = base_users.filter(branch_id=branch_id)

        active_users = base_users.filter(is_active=True, is_fired=False)
        total_employees = active_users.count()
        if total_employees == 0 and base_users.count() == 0:
            return {
                "summary": {},
                "weekly_dynamics": [],
                "today_status": {},
                "branch_ratings": [],
            }

        joined_this_month = active_users.filter(
            date_joined__date__gte=first_day_of_month
        ).count()
        users_before_this_month = total_employees - joined_this_month

        if users_before_this_month <= 0:
            emp_trend_val = 100.0 if joined_this_month > 0 else 0.0
        else:
            emp_trend_val = round(
                (joined_this_month / users_before_this_month) * 100, 1
            )

        unique_schedules = set([u.schedule for u in base_users])
        start_of_week = end_date - timedelta(days=end_date.weekday())
        week_days_dates = [start_of_week + timedelta(days=i) for i in range(7)]

        min_date = min(start_date, prev_start_date, start_of_week)
        max_date = max(end_date, prev_end_date, week_days_dates[-1])

        global_schedule_map = {}
        for sch in unique_schedules:
            global_schedule_map[sch] = ScheduleHelper.get_period_schedule(
                sch, min_date, max_date
            )

        def get_stats_for_period(s_date, e_date, users):
            atts = Attendance.objects.filter(
                user__in=users,
                created_at__date__gte=s_date,
                created_at__date__lte=e_date,
            )
            user_date_atts = {}
            for a in atts:
                if a.user_id not in user_date_atts:
                    user_date_atts[a.user_id] = {}
                d = timezone.localtime(a.created_at).date()
                if d not in user_date_atts[a.user_id]:
                    user_date_atts[a.user_id][d] = []
                user_date_atts[a.user_id][d].append(a)

            arrived = 0
            lates = 0
            early_leaves = 0
            expected = 0

            for u in users:
                sch_map = global_schedule_map.get(u.schedule)
                if not sch_map:
                    continue

                user_start_date = timezone.localtime(u.created_at).date()
                user_end_date = (
                    timezone.localtime(u.fired_at).date()
                    if u.is_fired and u.fired_at
                    else e_date
                )

                curr = max(s_date, user_start_date)
                actual_e_date = min(e_date, user_end_date)

                while curr <= actual_e_date:
                    u_atts = user_date_atts.get(u.id, {}).get(curr, [])
                    info = sch_map.get(curr)

                    if not info:
                        if u_atts:
                            has_record = any(
                                a.event_type
                                in (
                                    Attendance.EventType.CHECK_IN,
                                    Attendance.EventType.CHECK_OUT,
                                )
                                for a in u_atts
                            )
                            if has_record:
                                expected += 1
                                arrived += 1
                        curr += timedelta(days=1)
                        continue

                    is_mand = info["is_mandatory"]
                    if is_mand:
                        expected += 1

                    if u_atts:
                        check_ins = [
                            a
                            for a in u_atts
                            if a.event_type == Attendance.EventType.CHECK_IN
                        ]
                        check_outs = [
                            a
                            for a in u_atts
                            if a.event_type == Attendance.EventType.CHECK_OUT
                        ]

                        if check_ins or check_outs:
                            if info["is_optional"] or not (
                                info["is_mandatory"] or info["is_optional"]
                            ):
                                expected += 1
                            arrived += 1

                        if check_ins:
                            first_in = min(
                                [
                                    timezone.localtime(a.created_at).time()
                                    for a in check_ins
                                ]
                            )
                            if first_in > info["start_time"]:
                                lates += 1

                        if check_outs:
                            last_out = max(
                                [
                                    timezone.localtime(a.created_at).time()
                                    for a in check_outs
                                ]
                            )
                            if last_out < info["end_time"]:
                                early_leaves += 1
                    curr += timedelta(days=1)

            absent = expected - arrived if expected > arrived else 0
            pct = (arrived / expected * 100) if expected > 0 else 0

            return arrived, lates, early_leaves, absent, pct

        cur_arrived, cur_lates, cur_early, cur_absent, cur_pct = 0, 0, 0, 0, 0
        prv_arrived, prv_lates, prv_early, prv_absent, prv_pct = 0, 0, 0, 0, 0

        if "summary" in widgets:
            cur_arrived, cur_lates, cur_early, cur_absent, cur_pct = (
                get_stats_for_period(start_date, end_date, base_users)
            )
            prv_arrived, prv_lates, prv_early, prv_absent, prv_pct = (
                get_stats_for_period(prev_start_date, prev_end_date, base_users)
            )

        def calc_trend(cur, prv):
            if prv == 0:
                return 0.0 if cur == 0 else 100.0
            diff = ((cur - prv) / prv) * 100
            return round(diff, 1)

        day_names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
        weekly_dynamics = []
        if "weekly_dynamics" in widgets:
            for i, day in enumerate(week_days_dates):
                d_arrived, d_lates, _, _, _ = get_stats_for_period(day, day, base_users)
                d_on_time = d_arrived - d_lates
                weekly_dynamics.append(
                    {
                        "day_name": day_names[i],
                        "date": day.isoformat(),
                        "on_time": d_on_time,
                        "late": d_lates,
                    }
                )

        today_status = {}
        if "today_status" in widgets:
            t_arrived, t_lates, t_early, t_absent, t_pct = get_stats_for_period(
                end_date, end_date, base_users
            )
            today_status = {
                "on_time": t_arrived - t_lates,
                "late": t_lates,
                "early_left": t_early,
                "absent": t_absent,
                "total_percent": round(t_pct, 1),
            }

        branch_ratings = []
        if "branch_ratings" in widgets:
            from apps.analytics.reports import ReportService

            branch_report = ReportService.get_report_by_branch(
                user, start_date, end_date, region_id, district_id, branch_id
            )

            for b_data in branch_report["results"]:
                kpi_str = str(b_data["discipline_kpi"]).replace("%", "")
                try:
                    rating = float(kpi_str)
                except ValueError:
                    rating = 0
                branch_ratings.append({"name": b_data["branch"], "rating": rating})

            branch_ratings.sort(key=lambda x: x["rating"], reverse=True)
            branch_ratings = branch_ratings[:10]

        return {
            "summary": {
                "total_employees": total_employees,
                "total_employees_trend": emp_trend_val,
                "period_arrived": cur_arrived,
                "attendance_percent": round(cur_pct, 1),
                "lates": cur_lates,
                "lates_trend": calc_trend(cur_lates, prv_lates),
                "early_leaves": cur_early,
                "early_leaves_trend": calc_trend(cur_early, prv_early),
                "absent": cur_absent,
                "absent_trend": calc_trend(cur_absent, prv_absent),
            },
            "weekly_dynamics": weekly_dynamics,
            "today_status": today_status,
            "branch_ratings": branch_ratings,
        }
