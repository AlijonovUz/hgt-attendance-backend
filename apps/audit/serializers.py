from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_full_name",
            "action",
            "action_display",
            "table_name",
            "record_id",
            "object_name",
            "old_values",
            "new_values",
            "ip_address",
            "created_at",
        ]
