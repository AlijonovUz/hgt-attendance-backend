import logging
from datetime import timedelta
from django.utils import timezone
from apps.users.models import User, Branch
from apps.analytics.services.schedule import ScheduleHelper
from apps.analytics.services.reports import ReportService

logger = logging.getLogger(__name__)

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
            from django.db.models import Sum
            from apps.analytics.models import DailyAttendance

            stats = DailyAttendance.objects.filter(
                user__in=users,
                date__range=(s_date, e_date)
            ).aggregate(
                arrived=Sum('present'),
                lates=Sum('late'),
                early_leaves=Sum('left_early'),
                expected=Sum('total_expected'),
                absent=Sum('absent')
            )

            expected = stats['expected'] or 0
            arrived = stats['arrived'] or 0
            lates = stats['lates'] or 0
            early_leaves = stats['early_leaves'] or 0
            absent = stats['absent'] or 0

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
            from apps.analytics.services import ReportService

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
