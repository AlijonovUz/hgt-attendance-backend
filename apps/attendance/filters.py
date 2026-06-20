import django_filters

from .models import Attendance, Geozone, FaceLog, GpsLog, SignatureLog


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


class BaseLogFilter(django_filters.FilterSet):
    start_date = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    end_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    region = django_filters.CharFilter(field_name="user__branch__region")
    district = django_filters.CharFilter(field_name="user__branch__district")
    branch = django_filters.CharFilter(field_name="user__branch")


class FaceLogFilter(BaseLogFilter):
    class Meta:
        model = FaceLog
        fields = ["user", "is_success", "region", "district", "branch"]


class GpsLogFilter(BaseLogFilter):
    class Meta:
        model = GpsLog
        fields = ["user", "is_success", "region", "district", "branch"]


class SignatureLogFilter(BaseLogFilter):
    class Meta:
        model = SignatureLog
        fields = ["user", "is_valid", "region", "district", "branch"]
