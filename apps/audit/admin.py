from apps.utils.admin import BaseModelAdmin as ModelAdmin
from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ["user", "action", "table_name", "object_name", "created_at"]
    search_fields = ["user__full_name", "table_name", "object_name", "record_id"]
    list_filter = ["action", "table_name", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
