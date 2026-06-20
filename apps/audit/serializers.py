from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    region = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    branch = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_full_name",
            "region",
            "district",
            "branch",
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

    def get_region(self, obj):
        if obj.user and obj.user.branch and obj.user.branch.region:
            return {
                "id": obj.user.branch.region.id,
                "name": obj.user.branch.region.name,
            }
        return None

    def get_district(self, obj):
        if obj.user and obj.user.branch and obj.user.branch.district:
            return {
                "id": obj.user.branch.district.id,
                "name": obj.user.branch.district.name,
            }
        return None

    def get_branch(self, obj):
        if obj.user and obj.user.branch:
            return {"id": obj.user.branch.id, "name": obj.user.branch.name}
        return None
