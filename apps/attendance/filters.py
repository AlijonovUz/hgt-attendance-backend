import django_filters

from .models import Attendance, Geozone


class AttendanceFilter(django_filters.FilterSet):
    date_from = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    date_to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Attendance
        fields = [
            "user",
            "event_type",
            "face_verify",
            "user__department",
            "user__branch",
        ]


class GeozoneFilter(django_filters.FilterSet):
    class Meta:
        model = Geozone
        fields = [
            "branch",
            "branch__region",
            "branch__district",
            "zone_type",
        ]

