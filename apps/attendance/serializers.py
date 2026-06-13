from django.utils import timezone
from rest_framework import serializers

from apps.utils.face import hash_compare
from apps.utils.geo import haversine
from apps.users.serializers import UserShortInfoSerializer
from apps.notifications.models import Notification
from datetime import time

from .models import Attendance, Geozone, FaceLog, GpsLog


class GeozoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Geozone
        exclude = ["is_active"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceListSerializer(serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "user",
            "user_info",
            "event_type",
            "gps_latitude",
            "gps_longitude",
            "face_verify",
            "created_at",
        ]
        extra_kwargs = {"user": {"write_only": True}}


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
        min_distance = float("inf")
        for gz in user_geozones:
            distance = haversine(
                float(lat), float(lon), float(gz.latitude), float(gz.longitude)
            )
            if distance < min_distance:
                min_distance = distance
            if distance <= float(gz.radius):
                in_geozone = True
                break

        GpsLog.objects.create(
            user=user,
            is_success=in_geozone,
            latitude=lat,
            longitude=lon,
            distance_meters=min_distance if min_distance != float("inf") else None,
            message="Ichida" if in_geozone else "Tashqarida",
        )

        if not in_geozone:
            Notification.objects.create(
                user=user,
                title="Geozonadan tashqarida urunish",
                message="Siz ish joyi geozonasidan tashqarida qayd etilishga urindingiz.",
                extra_data={"event": "OUT_OF_ZONE"},
            )
            raise serializers.ValidationError({"detail": "Siz ish joyida emassiz."})

        if not user.face_image or not user.face_image.name:
            raise serializers.ValidationError(
                {"detail": "Face ID ga rasm yuklanmagan."}
            )

        is_verified, msg = hash_compare(user, image)

        FaceLog.objects.create(user=user, is_success=is_verified, message=msg)

        if not is_verified:
            raise serializers.ValidationError({"detail": msg})

        attrs["face_verify"] = True
        return attrs

    def create(self, validated_data):
        validated_data.pop("image", None)
        validated_data["user"] = self.context["request"].user
        instance = super().create(validated_data)

        user = instance.user
        event = instance.event_type
        current_time = timezone.localtime(instance.created_at).time()

        st = time(9, 0)
        let = time(14, 0)
        et = time(18, 0)

        if hasattr(user, "schedule") and user.schedule:
            st = user.schedule.work_start_time
            let = user.schedule.lunch_end_time
            et = user.schedule.work_end_time

        if event == Attendance.EventType.CHECK_IN and current_time > st:
            Notification.objects.create(
                user=user,
                title="Kechikish",
                message=f"Siz bugun ishga kechikib keldingiz. (Belgilangan vaqt: {st.strftime('%H:%M')})",
                extra_data={"event": "LATE_CHECK_IN"},
            )
        elif event == Attendance.EventType.LUNCH_END and let is not None and current_time > let:
            Notification.objects.create(
                user=user,
                title="Tushlikdan kechikish",
                message=f"Siz tushlikdan kech qaytdingiz. (Belgilangan vaqt: {let.strftime('%H:%M')})",
                extra_data={"event": "LATE_LUNCH_RETURN"},
            )
        elif event == Attendance.EventType.CHECK_OUT and current_time < et:
            Notification.objects.create(
                user=user,
                title="Erta ketish",
                message=f"Siz ish vaqti tugamasdan oldin ketdingiz. (Belgilangan vaqt: {et.strftime('%H:%M')})",
                extra_data={"event": "EARLY_CHECK_OUT"},
            )

        return instance
