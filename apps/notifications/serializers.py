from rest_framework import serializers

from .models import Notification, UserDevice


class NotificationSerializer(serializers.ModelSerializer):
    """
    3 dildagi bildirishnoma matni va sarlavhalarini qaytaruvchi API serializatori.
    """
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
    """
    Foydalanuvchi mobil qurilmalarini ro'yxatga olish uchun serializator.
    Tokenlarni validatsiya qiladi.
    """
    class Meta:
        model = UserDevice
        fields = ("id", "user", "fcm_token", "device_type", "device_id", "created_at")
        read_only_fields = ("id", "user", "created_at")
        extra_kwargs = {
            "fcm_token": {"validators": []},
            "device_id": {"validators": []},
        }
