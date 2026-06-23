import django_filters
from .models import KPIResult, DailyAttendance


class KPIResultFilter(django_filters.FilterSet):
    region = django_filters.CharFilter(field_name="user__branch__region")
    district = django_filters.CharFilter(field_name="user__branch__district")
    branch = django_filters.CharFilter(field_name="user__branch")
    department = django_filters.CharFilter(field_name="user__department")
    start_date = django_filters.DateFilter(
        field_name="month", lookup_expr="gte"
    )
    end_date = django_filters.DateFilter(
        field_name="month", lookup_expr="lte"
    )

    class Meta:
        model = KPIResult
        fields = ["user", "month", "rating_category", "region", "district", "branch", "department"]


class DailyAttendanceFilter(django_filters.FilterSet):
    region = django_filters.CharFilter(field_name="user__branch__region")
    district = django_filters.CharFilter(field_name="user__branch__district")
    branch = django_filters.CharFilter(field_name="user__branch")
    department = django_filters.CharFilter(field_name="user__department")
    start_date = django_filters.DateFilter(
        field_name="date", lookup_expr="gte"
    )
    end_date = django_filters.DateFilter(
        field_name="date", lookup_expr="lte"
    )

    class Meta:
        model = DailyAttendance
        fields = [
            "user",
            "date",
            "schedule_name",
            "is_mandatory",
            "is_holiday",
            "region",
            "district",
            "branch",
            "department",
        ]
