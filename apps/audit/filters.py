import django_filters

from .models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__gte"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__lte"
    )
    region = django_filters.CharFilter(field_name="user__branch__region")
    district = django_filters.CharFilter(field_name="user__branch__district")
    branch = django_filters.CharFilter(field_name="user__branch")

    class Meta:
        model = AuditLog
        fields = ["user", "action", "table_name", "region", "district", "branch"]
