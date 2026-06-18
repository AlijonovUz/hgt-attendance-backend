from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters

from apps.utils.views import BaseReadOnlyViewSet

from .filters import AuditLogFilter
from .models import AuditLog
from .serializers import AuditLogSerializer


@extend_schema(tags=["Audit jurnallari"])
class AuditLogViewSet(BaseReadOnlyViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = AuditLogFilter
    search_fields = [
        "table_name",
        "record_id",
        "object_name",
        "user__full_name",
        "ip_address",
    ]
    http_method_names = ["get", "head", "options"]

    action_permissions = {
        "list": "audit_view",
        "retrieve": "audit_view",
    }
