from datetime import datetime, date, timedelta
from django.utils import timezone
from apps.users.models import User
from apps.attendance.models import Attendance


class ReportService:
    @staticmethod
    def _get_users(request_user, region_id=None, district_id=None, branch_id=None):
        users = User.objects.all()
        if not (
            request_user.is_superuser
            or request_user.has_permission("analytics_view_all")
        ):
            if (
                request_user.has_permission("analytics_view_region")
                and request_user.branch
                and request_user.branch.region
            ):
                users = users.filter(branch__region=request_user.branch.region)
            elif (
                request_user.has_permission("analytics_view_district")
                and request_user.branch
                and request_user.branch.district
            ):
                users = users.filter(branch__district=request_user.branch.district)
            elif (
                request_user.has_permission("analytics_view_branch")
                and request_user.branch
            ):
                users = users.filter(branch=request_user.branch)
            elif (
                request_user.has_permission("analytics_view_dept")
                and request_user.department
            ):
                users = users.filter(department=request_user.department)
            else:
                users = users.filter(id=request_user.id)

        if region_id:
            users = users.filter(branch__region_id=region_id)
        if district_id:
            users = users.filter(branch__district_id=district_id)
        if branch_id:
            users = users.filter(branch_id=branch_id)

        return users

    @staticmethod
    def _calculate_stats(users, start_date, end_date):
        from apps.analytics.services import ScheduleHelper

        start_dt = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time())
        )
        end_dt = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        attendances = Attendance.objects.filter(
            user_id__in=users.values("id"), created_at__range=(start_dt, end_dt)
        ).order_by("created_at")

        from django.db.models import Sum
        from apps.analytics.models import DailyAttendance
        
        today = timezone.localtime().date()
        from apps.analytics.services.daily import DailyKPIService
        
        target_calc_date = min(end_date, today)
        for u in users:
            DailyKPIService.calculate_daily_snapshot(u, target_calc_date)
            DailyKPIService.calculate_daily_snapshot(u, target_calc_date - timedelta(days=1))

        all_stats = DailyAttendance.objects.filter(
            user__in=users,
            date__range=(start_date, end_date)
        ).values('user').annotate(
            total_expected=Sum('total_expected'),
            present=Sum('present'),
            absent=Sum('absent'),
            late=Sum('late'),
            left_early=Sum('left_early'),
        )

        stats_map = {item['user']: item for item in all_stats}
        user_stats = {}

        for user in users:
            user_stat = stats_map.get(user.id, {})
            
            total_expected = user_stat.get('total_expected') or 0
            present = user_stat.get('present') or 0
            late = user_stat.get('late') or 0
            absent = user_stat.get('absent') or 0
            left_early = user_stat.get('left_early') or 0

            on_time_in = max(0, present - late)
            on_time_out = max(0, present - left_early)
            compliant_actions = on_time_in + on_time_out
            total_expected_actions = total_expected * 2

            attendance_kpi = 0
            monthly_kpi = 0
            discipline_kpi = 0

            if total_expected > 0:
                attendance_kpi = (on_time_in / total_expected) * 100
                monthly_kpi = ((on_time_in + on_time_out) / (total_expected * 2)) * 100

                discipline_coefficient = (
                    (compliant_actions / total_expected_actions)
                    if total_expected_actions > 0
                    else 0
                )

                total_score = (
                    monthly_kpi + attendance_kpi + (discipline_coefficient * 100)
                ) / 3
                discipline_kpi = round(total_score)
            else:
                discipline_kpi = 0
                total_expected_actions = 0

            user_stats[user.id] = {
                "user": user,
                "total_expected": total_expected,
                "present": present,
                "late": late,
                "absent": absent,
                "left_early": left_early,
                "discipline_kpi": discipline_kpi,
                "total_actions_expected": total_expected_actions,
                "compliant_actions": compliant_actions,
            }
        return user_stats

    @staticmethod
    def get_report_by_employee(
        request_user,
        start_date: date,
        end_date: date,
        region_id=None,
        district_id=None,
        branch_id=None,
        status=None,
    ):
        users = ReportService._get_users(
            request_user, region_id, district_id, branch_id
        ).select_related(
            "department", "position", "branch", "branch__region", "branch__district"
        )
        stats = ReportService._calculate_stats(users, start_date, end_date)

        report_data = []
        summary = {
            "total_expected": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
            "left_early": 0,
            "total_kpi": 0,
        }

        active_users_count = 0

        for user_id, stat in stats.items():
            if status == "present" and stat["present"] == 0:
                continue
            if status == "absent" and stat["absent"] == 0:
                continue
            if status == "late" and stat["late"] == 0:
                continue

            user = stat["user"]
            branch_name = user.branch.name if user.branch else None
            region_name = (
                user.branch.region.name if user.branch and user.branch.region else None
            )
            district_name = (
                user.branch.district.name
                if user.branch and user.branch.district
                else None
            )

            report_data.append(
                {
                    "id": user.id,
                    "full_name": user.full_name,
                    "department": user.department.name if user.department else None,
                    "position": user.position.name if user.position else None,
                    "branch": branch_name,
                    "region": region_name,
                    "district": district_name,
                    "total_expected": stat["total_expected"],
                    "present": stat["present"],
                    "late": stat["late"],
                    "absent": stat["absent"],
                    "left_early": stat["left_early"],
                    "discipline_kpi": f"{stat['discipline_kpi']}%",
                }
            )

            summary["total_expected"] += stat["total_expected"]
            summary["present"] += stat["present"]
            summary["late"] += stat["late"]
            summary["absent"] += stat["absent"]
            summary["left_early"] += stat["left_early"]

            if stat["total_expected"] > 0 or stat["present"] > 0:
                summary["total_kpi"] += stat["discipline_kpi"]
                active_users_count += 1

        avg_kpi = (
            round(summary["total_kpi"] / active_users_count)
            if active_users_count > 0
            else 0
        )

        return {
            "results": report_data,
            "summary": {
                "total_expected": summary["total_expected"],
                "present": summary["present"],
                "late": summary["late"],
                "absent": summary["absent"],
                "left_early": summary["left_early"],
                "discipline_kpi": f"{avg_kpi}%",
            },
        }

    @staticmethod
    def get_report_by_branch(
        request_user,
        start_date: date,
        end_date: date,
        region_id=None,
        district_id=None,
        branch_id=None,
    ):
        users = ReportService._get_users(
            request_user, region_id, district_id, branch_id
        ).select_related("branch", "branch__region", "branch__district")
        stats = ReportService._calculate_stats(users, start_date, end_date)

        branch_stats = {}
        for user_id, stat in stats.items():
            branch = stat["user"].branch
            if not branch:
                continue

            branch_id = branch.id
            branch_name = branch.name
            region_name = branch.region.name if branch.region else None
            district_name = branch.district.name if branch.district else None

            if branch_id not in branch_stats:
                branch_stats[branch_id] = {
                    "id": branch_id,
                    "name": branch_name,
                    "region": region_name,
                    "district": district_name,
                    "total_expected": 0,
                    "present": 0,
                    "late": 0,
                    "absent": 0,
                    "left_early": 0,
                    "total_kpi": 0,
                    "employee_count": 0,
                }

            b = branch_stats[branch_id]
            b["total_expected"] += stat["total_expected"]
            b["present"] += stat["present"]
            b["late"] += stat["late"]
            b["absent"] += stat["absent"]
            b["left_early"] += stat["left_early"]

            if stat["total_expected"] > 0 or stat["present"] > 0:
                b["total_kpi"] += stat["discipline_kpi"]
                b["employee_count"] += 1

        report_data = []
        summary = {
            "total_expected": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
            "left_early": 0,
            "total_kpi": 0,
        }

        active_branches_count = 0

        for b_id, b in branch_stats.items():
            avg_kpi = (
                round(b["total_kpi"] / b["employee_count"])
                if b["employee_count"] > 0
                else 0
            )
            report_data.append(
                {
                    "id": b["id"],
                    "branch": b["name"],
                    "region": b["region"],
                    "district": b["district"],
                    "total_expected": b["total_expected"],
                    "present": b["present"],
                    "late": b["late"],
                    "absent": b["absent"],
                    "left_early": b["left_early"],
                    "discipline_kpi": f"{avg_kpi}%",
                }
            )

            summary["total_expected"] += b["total_expected"]
            summary["present"] += b["present"]
            summary["late"] += b["late"]
            summary["absent"] += b["absent"]
            summary["left_early"] += b["left_early"]

            if b["employee_count"] > 0:
                summary["total_kpi"] += avg_kpi
                active_branches_count += 1

        overall_avg_kpi = (
            round(summary["total_kpi"] / active_branches_count)
            if active_branches_count > 0
            else 0
        )

        return {
            "results": report_data,
            "summary": {
                "total_expected": summary["total_expected"],
                "present": summary["present"],
                "late": summary["late"],
                "absent": summary["absent"],
                "left_early": summary["left_early"],
                "discipline_kpi": f"{overall_avg_kpi}%",
            },
        }
