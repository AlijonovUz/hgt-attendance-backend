from django.contrib import admin
from apps.utils.admin import BaseModelAdmin as ModelAdmin

from .models import KPIResult, DailyAttendance


@admin.register(KPIResult)
class KPIResultAdmin(ModelAdmin):
    list_display = [
        "user",
        "month",
        "attendance_kpi",
        "monthly_kpi",
        "rating_category",
        "total_score",
        "is_active",
    ]
    search_fields = ["user__full_name", "user__jshshir"]
    list_filter = ["month", "rating_category"]
    readonly_fields = [
        "user",
        "month",
        "total_work_days",
        "attended_days",
        "lates_count",
        "left_early_count",
        "attendance_kpi",
        "monthly_kpi",
        "late_coefficient",
        "discipline_coefficient",
        "total_score",
        "rating_category",
    ]

    def has_add_permission(self, request):
        return False


@admin.register(DailyAttendance)
class DailyAttendanceAdmin(ModelAdmin):
    list_display = [
        "user",
        "date",
        "schedule_name",
        "present",
        "absent",
        "late",
        "left_early",
        "is_active",
    ]
    search_fields = ["user__full_name", "user__jshshir", "schedule_name"]
    list_filter = ["date", "is_mandatory", "is_holiday", "present", "absent", "late"]
    readonly_fields = [
        "user",
        "date",
        "schedule_name",
        "is_mandatory",
        "is_holiday",
        "total_expected",
        "present",
        "absent",
        "late",
        "left_early",
    ]

    def has_add_permission(self, request):
        return False
