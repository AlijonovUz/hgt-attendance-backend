from rest_framework import serializers
from apps.users.serializers import UserShortInfoSerializer
from .models import KPIResult, DailyAttendance
from apps.utils.serializers import RegionDistrictBranchMixin


class KPIResultSerializer(RegionDistrictBranchMixin, serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)
    rating_display = serializers.CharField(
        source="get_rating_category_display", read_only=True
    )

    class Meta:
        model = KPIResult
        fields = [
            "id",
            "user",
            "user_info",
            "region",
            "district",
            "branch",
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
            "rating_display",
            "created_at",
            "updated_at",
        ]


class DailyAttendanceSerializer(RegionDistrictBranchMixin, serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)

    class Meta:
        model = DailyAttendance
        fields = [
            "id",
            "user",
            "user_info",
            "region",
            "district",
            "branch",
            "date",
            "schedule_name",
            "is_mandatory",
            "is_holiday",
            "total_expected",
            "present",
            "absent",
            "late",
            "left_early",
            "created_at",
            "updated_at",
        ]
