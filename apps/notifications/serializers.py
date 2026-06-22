from rest_framework import serializers

from .models import Notification, UserDevice


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "title_uz_latn",
            "title_uz_cyrl",
            "title_ru",
            "message_uz_latn",
            "message_uz_cyrl",
            "message_ru",
            "extra_data",
            "is_read",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ("id", "user", "fcm_token", "device_type", "device_id", "created_at")
        read_only_fields = ("id",)
