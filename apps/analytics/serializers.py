from rest_framework import serializers
from apps.users.serializers import UserShortInfoSerializer
from .models import KPIResult

class KPIResultSerializer(serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)
    rating_display = serializers.CharField(source="get_rating_category_display", read_only=True)

    class Meta:
        model = KPIResult
        fields = [
            "id",
            "user",
            "user_info",
            "month",
            "total_work_days",
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
            "rating_display",
            "created_at",
            "updated_at",
        ]
