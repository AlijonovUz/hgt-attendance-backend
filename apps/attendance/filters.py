import django_filters

from .models import Attendance, Geozone


class AttendanceFilter(django_filters.FilterSet):
    start_date = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    end_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    department = django_filters.CharFilter(field_name="user__department")
    branch = django_filters.CharFilter(field_name="user__branch")

    class Meta:
        model = Attendance
        fields = [
            "user",
            "event_type",
            "face_verify",
            "department",
            "branch",
        ]


class GeozoneFilter(django_filters.FilterSet):
    region = django_filters.CharFilter(field_name="branch__region")
    district = django_filters.CharFilter(field_name="branch__district")

    class Meta:
        model = Geozone
        fields = [
            "branch",
            "region",
            "district",
            "zone_type",
        ]
