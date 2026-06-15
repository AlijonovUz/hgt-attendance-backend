from datetime import datetime, date, timedelta
from django.utils import timezone
from apps.users.models import User
from apps.attendance.models import Attendance
from apps.analytics.services import ScheduleHelper

class ReportService:
    @staticmethod
    def _get_users(request_user):
        if request_user.is_superuser or request_user.has_permission("analytics_view_all"):
            return User.objects.all()
        if request_user.has_permission("analytics_view_dept") and request_user.department:
            return User.objects.filter(department=request_user.department)
        return User.objects.filter(id=request_user.id)

    @staticmethod
    def _calculate_stats(users, start_date, end_date):
        start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        
        attendances = Attendance.objects.filter(
            user__in=users, 
            created_at__range=(start_dt, end_dt)
        ).order_by('created_at')

        att_by_user_day = {}
        for att in attendances:
            day = timezone.localtime(att.created_at).date()
            if att.user_id not in att_by_user_day:
                att_by_user_day[att.user_id] = {}
            if day not in att_by_user_day[att.user_id]:
                att_by_user_day[att.user_id][day] = []
            att_by_user_day[att.user_id][day].append(att)

        user_stats = {}
        today = timezone.localtime().date()
        
        for user in users:
            schedule_map = ScheduleHelper.get_period_schedule(user.schedule, start_date, end_date)
            
            total_expected = 0
            present = 0
            late = 0
            absent = 0
            left_early = 0

            curr = start_date
            while curr <= min(end_date, today):
                day_info = schedule_map.get(curr)
                if day_info and day_info["is_mandatory"]:
                    total_expected += 1
                    day_atts = att_by_user_day.get(user.id, {}).get(curr, [])
                    
                    check_in = next((a for a in day_atts if a.event_type == Attendance.EventType.CHECK_IN), None)
                    check_out = next((a for a in day_atts if a.event_type == Attendance.EventType.CHECK_OUT), None)

                    if check_in:
                        present += 1
                        check_in_time = timezone.localtime(check_in.created_at).time()
                        if check_in_time > day_info["start_time"]:
                            late += 1
                        if check_out:
                            check_out_time = timezone.localtime(check_out.created_at).time()
                            if check_out_time < day_info["end_time"]:
                                left_early += 1
                    else:
                        absent += 1
                curr += timedelta(days=1)
                
            penalty = (late + left_early) * 5
            discipline_kpi = max(0, 100 - penalty)
            
            user_stats[user.id] = {
                "user": user,
                "total_expected": total_expected,
                "present": present,
                "late": late,
                "absent": absent,
                "left_early": left_early,
                "discipline_kpi": discipline_kpi
            }
        return user_stats

    @staticmethod
    def get_report_by_employee(request_user, start_date: date, end_date: date):
        users = ReportService._get_users(request_user).select_related('branch', 'department')
        stats = ReportService._calculate_stats(users, start_date, end_date)
        
        report_data = []
        summary = {
            "total_expected": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
            "left_early": 0,
            "total_kpi": 0
        }

        for user_id, stat in stats.items():
            user = stat["user"]
            report_data.append({
                "id": user.id,
                "full_name": user.full_name,
                "branch": user.branch.name if user.branch else None,
                "department": user.department.name if user.department else None,
                "total_expected": stat["total_expected"],
                "present": stat["present"],
                "late": stat["late"],
                "absent": stat["absent"],
                "left_early": stat["left_early"],
                "discipline_kpi": f"{stat['discipline_kpi']}%"
            })
            
            summary["total_expected"] += stat["total_expected"]
            summary["present"] += stat["present"]
            summary["late"] += stat["late"]
            summary["absent"] += stat["absent"]
            summary["left_early"] += stat["left_early"]
            summary["total_kpi"] += stat["discipline_kpi"]

        avg_kpi = round(summary["total_kpi"] / len(report_data)) if report_data else 0
        
        return {
            "results": report_data,
            "summary": {
                "total_expected": summary["total_expected"],
                "present": summary["present"],
                "late": summary["late"],
                "absent": summary["absent"],
                "left_early": summary["left_early"],
                "discipline_kpi": f"{avg_kpi}%"
            }
        }

    @staticmethod
    def get_report_by_branch(request_user, start_date: date, end_date: date):
        users = ReportService._get_users(request_user).select_related('branch')
        stats = ReportService._calculate_stats(users, start_date, end_date)
        
        branch_stats = {}
        for user_id, stat in stats.items():
            branch_id = stat["user"].branch_id
            branch_name = stat["user"].branch.name if stat["user"].branch else "Boshqa"
            
            if branch_id not in branch_stats:
                branch_stats[branch_id] = {
                    "id": branch_id,
                    "name": branch_name,
                    "total_expected": 0,
                    "present": 0,
                    "late": 0,
                    "absent": 0,
                    "left_early": 0,
                    "total_kpi": 0,
                    "employee_count": 0
                }
            
            b = branch_stats[branch_id]
            b["total_expected"] += stat["total_expected"]
            b["present"] += stat["present"]
            b["late"] += stat["late"]
            b["absent"] += stat["absent"]
            b["left_early"] += stat["left_early"]
            b["total_kpi"] += stat["discipline_kpi"]
            b["employee_count"] += 1

        report_data = []
        summary = {
            "total_expected": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
            "left_early": 0,
            "total_kpi": 0
        }

        for b_id, b in branch_stats.items():
            avg_kpi = round(b["total_kpi"] / b["employee_count"]) if b["employee_count"] > 0 else 0
            report_data.append({
                "id": b["id"],
                "branch": b["name"],
                "total_expected": b["total_expected"],
                "present": b["present"],
                "late": b["late"],
                "absent": b["absent"],
                "left_early": b["left_early"],
                "discipline_kpi": f"{avg_kpi}%"
            })
            
            summary["total_expected"] += b["total_expected"]
            summary["present"] += b["present"]
            summary["late"] += b["late"]
            summary["absent"] += b["absent"]
            summary["left_early"] += b["left_early"]
            summary["total_kpi"] += avg_kpi

        overall_avg_kpi = round(summary["total_kpi"] / len(report_data)) if report_data else 0
        
        return {
            "results": report_data,
            "summary": {
                "total_expected": summary["total_expected"],
                "present": summary["present"],
                "late": summary["late"],
                "absent": summary["absent"],
                "left_early": summary["left_early"],
                "discipline_kpi": f"{overall_avg_kpi}%"
            }
        }
