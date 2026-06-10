from django.utils import timezone
from rest_framework import serializers

from apps.utils.services import hash_compare, haversine

from .models import Attendance, Geozone


class GeozoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Geozone
        exclude = ["is_active"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "user_full_name",
            "event_type",
            "gps_latitude",
            "gps_longitude",
            "face_verify",
            "created_at",
        ]


class AttendanceCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        write_only=True, required=True, label="Yuzni tekshirish uchun rasm"
    )

    class Meta:
        model = Attendance
        fields = ["event_type", "gps_latitude", "gps_longitude", "image"]

    def validate(self, attrs):
        user = self.context["request"].user
        lat = attrs.get("gps_latitude")
        lon = attrs.get("gps_longitude")
        image = attrs.get("image")
        event_type = attrs.get("event_type")

        today = timezone.now().date()
        todays_events = Attendance.objects.filter(
            user=user, created_at__date=today
        ).values_list("event_type", flat=True)

        if event_type in todays_events:
            event_name = dict(Attendance.EventType.choices).get(event_type, event_type)
            raise serializers.ValidationError(
                {
                    "detail": f"Siz bugun allaqachon '{event_name}' holatini qayd etgansiz!"
                }
            )

        if (
            event_type == Attendance.EventType.LUNCH_START
            and Attendance.EventType.CHECK_IN not in todays_events
        ):
            raise serializers.ValidationError(
                {"detail": "Avval ishga kelishni qayd eting."}
            )

        if (
            event_type == Attendance.EventType.LUNCH_END
            and Attendance.EventType.LUNCH_START not in todays_events
        ):
            raise serializers.ValidationError(
                {"detail": "Hali tushlikka chiqmagansiz."}
            )

        if (
            event_type == Attendance.EventType.CHECK_OUT
            and Attendance.EventType.CHECK_IN not in todays_events
        ):
            raise serializers.ValidationError(
                {"detail": "Avval ishga kelishni qayd eting."}
            )

        if not user.branch:
            raise serializers.ValidationError(
                {"detail": "Filialga biriktirilmagansiz."}
            )

        user_geozones = user.branch.geozones.active()
        if not user_geozones.exists():
            raise serializers.ValidationError(
                {"detail": "Ish joyiga biriktirilgan faol geozona topilmadi."}
            )

        in_geozone = False
        min_distance = float('inf')
        for gz in user_geozones:
            distance = haversine(
                float(lat), float(lon), float(gz.latitude), float(gz.longitude)
            )
            if distance < min_distance:
                min_distance = distance
            if distance <= float(gz.radius):
                in_geozone = True
                break
        
        from .models import GpsLog
        GpsLog.objects.create(
            user=user,
            is_success=in_geozone,
            latitude=lat,
            longitude=lon,
            distance_meters=min_distance if min_distance != float('inf') else None,
            message="Ichida" if in_geozone else "Tashqarida"
        )

        if not in_geozone:
            raise serializers.ValidationError({"detail": "Siz ish joyida emassiz."})

        if not user.face_image or not user.face_image.name:
            raise serializers.ValidationError(
                {"detail": "Face ID ga rasm yuklanmagan."}
            )

        is_verified, msg = hash_compare(user, image)
        
        from .models import FaceLog
        FaceLog.objects.create(
            user=user,
            is_success=is_verified,
            message=msg
        )
        
        if not is_verified:
            raise serializers.ValidationError({"detail": msg})

        attrs["face_verify"] = True
        return attrs

    def create(self, validated_data):
        validated_data.pop("image", None)
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
