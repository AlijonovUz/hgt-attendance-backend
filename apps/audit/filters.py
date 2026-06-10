import django_filters

from .models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    date_to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["user", "action", "table_name"]
