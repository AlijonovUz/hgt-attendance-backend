import django_filters

from .models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    start_date = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    end_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["user", "action", "table_name"]
