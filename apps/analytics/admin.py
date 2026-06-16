from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import KPIResult


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
        "days_arrived_on_time",
        "days_left_on_time",
        "lates_count",
        "total_actions_expected",
        "compliant_actions",
        "attendance_kpi",
        "monthly_kpi",
        "late_coefficient",
        "discipline_coefficient",
        "total_score",
        "rating_category",
    ]

    def has_add_permission(self, request):
        return False
