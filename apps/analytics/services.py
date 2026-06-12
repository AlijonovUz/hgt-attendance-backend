import logging
import calendar
from datetime import date, datetime, time, timedelta
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.analytics.models import KPIResult
from apps.users.models import User, Branch

logger = logging.getLogger(__name__)


class KPIService:
    @staticmethod
    def get_work_days(year, month):
        today = timezone.localtime().date()
        _, num_days = calendar.monthrange(year, month)

        work_days = 0
        for day in range(1, num_days + 1):
            d = date(year, month, day)
            if d > today:
                break
            if d.weekday() < 5:
                work_days += 1

        return work_days

    @classmethod
    def calculate_user_kpi(cls, user, year, month):
        work_days = cls.get_work_days(year, month)
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
            check_ins = [
                a for a in atts if a.event_type == Attendance.EventType.CHECK_IN
            ]
            if check_ins:
                first_in = min(
                    [timezone.localtime(a.created_at).time() for a in check_ins]
                )
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

            lunch_ends = [
                a for a in atts if a.event_type == Attendance.EventType.LUNCH_END
            ]
            if lunch_ends:
                first_lunch_end = min(
                    [timezone.localtime(a.created_at).time() for a in lunch_ends]
                )
                if first_lunch_end <= time(14, 0, 0):
                    compliant_actions += 1

            check_outs = [
                a for a in atts if a.event_type == Attendance.EventType.CHECK_OUT
            ]
            if check_outs:
                last_out = max(
                    [timezone.localtime(a.created_at).time() for a in check_outs]
                )
                if last_out >= time(18, 0, 0):
                    days_left_on_time += 1
                    compliant_actions += 1

        total_expected_actions = work_days * 4

        attendance_kpi = (
            (days_arrived_on_time / work_days * 100) if work_days > 0 else 0
        )

        monthly_kpi = (
            ((days_arrived_on_time + days_left_on_time) / (work_days * 2)) * 100
            if work_days > 0
            else 0
        )

        late_coefficient = lates_count / work_days if work_days > 0 else 0

        discipline_coefficient = (
            (compliant_actions / total_expected_actions)
            if total_expected_actions > 0
            else 0
        )

        attendance_percentage = (len(grouped) / work_days * 100) if work_days > 0 else 0

        total_score = (
            monthly_kpi + attendance_percentage + (discipline_coefficient * 100)
        ) / 3
        total_score = round(total_score, 2)

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

        logger.info(
            "KPI hisoblandi: UserID=%s | Ball=%s | Kategoriya=%s",
            user.id,
            total_score,
            rating_category,
        )

        return kpi_result


class DashboardService:
    @staticmethod
    def get_dashboard_stats(user, start_date=None, end_date=None):
        today_date = timezone.localtime().date()

        if start_date is None or end_date is None:
            start_date = today_date
            end_date = today_date

        period_days = (end_date - start_date).days + 1

        prev_start_date = start_date - timedelta(days=period_days)
        prev_end_date = start_date - timedelta(days=1)

        first_day_of_month = end_date.replace(day=1)

        base_users = User.objects.filter(is_active=True, is_fired=False)

        if not (user.is_superuser or user.has_permission("analytics_view_all")):
            if user.has_permission("analytics_view_dept") and user.department:
                base_users = base_users.filter(department=user.department)
            else:
                logger.warning("Dashboard: Ruxsat yo'q. UserID=%s", user.id)
                return None

        total_employees = base_users.count()
        if total_employees == 0:
            return {
                "summary": {},
                "weekly_dynamics": [],
                "today_status": {},
                "branch_ratings": [],
            }

        joined_this_month = base_users.filter(
            date_joined__date__gte=first_day_of_month
        ).count()
        users_before_this_month = total_employees - joined_this_month

        if users_before_this_month == 0:
            emp_trend_str = f"+100.0% bu oy" if joined_this_month > 0 else "+0.0% bu oy"
        else:
            emp_trend = (joined_this_month / users_before_this_month) * 100
            emp_trend_str = (
                f"+{emp_trend:.1f}% bu oy"
                if emp_trend > 0
                else f"{emp_trend:.1f}% bu oy"
            )

        def get_work_days(s_date, e_date):
            wd = 0
            days = (e_date - s_date).days + 1
            for i in range(days):
                if (s_date + timedelta(days=i)).weekday() < 6:
                    wd += 1
            return wd

        current_work_days = get_work_days(start_date, end_date)
        prev_work_days = get_work_days(prev_start_date, prev_end_date)

        def get_stats_for_period(s_date, e_date, work_days):
            atts = Attendance.objects.filter(
                user__in=base_users,
                created_at__date__gte=s_date,
                created_at__date__lte=e_date,
            )
            check_ins = atts.filter(event_type=Attendance.EventType.CHECK_IN)
            arrived = check_ins.count()
            lates = check_ins.filter(created_at__time__gt=time(9, 0, 0)).count()
            early_leaves = atts.filter(
                event_type=Attendance.EventType.CHECK_OUT,
                created_at__time__lt=time(18, 0, 0),
            ).count()

            expected = total_employees * work_days
            absent = expected - arrived if expected > arrived else 0
            pct = (arrived / expected * 100) if expected > 0 else 0

            return arrived, lates, early_leaves, absent, pct

        cur_arrived, cur_lates, cur_early, cur_absent, cur_pct = get_stats_for_period(
            start_date, end_date, current_work_days
        )
        prv_arrived, prv_lates, prv_early, prv_absent, prv_pct = get_stats_for_period(
            prev_start_date, prev_end_date, prev_work_days
        )

        def calc_trend(cur, prv):
            if prv == 0:
                return "+0.0%" if cur == 0 else "+100.0%"
            diff = ((cur - prv) / prv) * 100
            return (
                f"+{diff:.1f}% oldingiga nisbatan"
                if diff > 0
                else f"{diff:.1f}% oldingiga nisbatan"
            )

        start_of_week = end_date - timedelta(days=end_date.weekday())
        week_days = [start_of_week + timedelta(days=i) for i in range(6)]
        day_names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh"]

        weekly_dynamics = []
        for i, day in enumerate(week_days):
            day_check_ins = Attendance.objects.filter(
                user__in=base_users,
                created_at__date=day,
                event_type=Attendance.EventType.CHECK_IN,
            )
            d_arrived = day_check_ins.count()
            d_lates = day_check_ins.filter(created_at__time__gt=time(9, 0, 0)).count()
            d_on_time = d_arrived - d_lates
            weekly_dynamics.append(
                {
                    "day_name": day_names[i],
                    "date": day.isoformat(),
                    "on_time": d_on_time,
                    "late": d_lates,
                }
            )

        today_status = {
            "on_time": cur_arrived - cur_lates,
            "late": cur_lates,
            "early_left": cur_early,
            "absent": cur_absent,
            "total_percent": round(cur_pct, 1),
        }

        branch_ratings = []
        if user.is_superuser or user.has_permission("analytics_view_all"):
            branches = Branch.objects.all()
            for branch in branches:
                branch_users = User.objects.filter(
                    branch=branch, is_active=True, is_fired=False
                )
                b_total = branch_users.count()
                if b_total == 0:
                    continue
                b_expected = b_total * current_work_days
                b_arrived = Attendance.objects.filter(
                    user__in=branch_users,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                    event_type=Attendance.EventType.CHECK_IN,
                ).count()
                b_percent = (b_arrived / b_expected * 100) if b_expected > 0 else 0
                branch_ratings.append({"name": branch.name, "rating": round(b_percent)})
            branch_ratings.sort(key=lambda x: x["rating"], reverse=True)

        logger.debug("Dashboard stats tayyorlandi: UserID=%s", user.id)

        return {
            "summary": {
                "total_employees": total_employees,
                "total_employees_trend": emp_trend_str,
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
