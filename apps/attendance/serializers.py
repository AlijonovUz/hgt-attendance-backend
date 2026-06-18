import hmac
import hashlib
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers

from apps.utils.face import hash_compare
from apps.utils.geo import haversine
from apps.users.serializers import UserShortInfoSerializer
from apps.notifications.models import Notification
from datetime import time

from .models import Attendance, Geozone, FaceLog, GpsLog, SignatureLog


class GeozoneSerializer(serializers.ModelSerializer):
    workers_count = serializers.SerializerMethodField()

    class Meta:
        model = Geozone
        exclude = ["is_active"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_workers_count(self, obj):
        if obj.branch:
            from apps.users.models import User
            return User.objects.filter(branch=obj.branch, is_active=True).count()
        return 0


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
    created_at = serializers.DateTimeField(required=False)
    signature = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Attendance
        fields = ["event_type", "gps_latitude", "gps_longitude", "image", "created_at", "signature"]

    def validate(self, attrs):
        user = self.context["request"].user
        lat = attrs.get("gps_latitude")
        lon = attrs.get("gps_longitude")
        image = attrs.get("image")
        event_type = attrs.get("event_type")

        provided_created_at = attrs.get("created_at")
        signature = attrs.get("signature")

        if provided_created_at:
            if not signature:
                raise serializers.ValidationError({"signature": "Vaqtni tasdiqlash uchun imzo (signature) kiritilishi shart."})
            
            secret_key = hashlib.sha256(user.password.encode('utf-8')).hexdigest()
            time_str = self.initial_data.get("created_at")
            
            expected_signature = hmac.new(
                secret_key.encode('utf-8'),
                str(time_str).encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_signature, signature):
                SignatureLog.objects.create(user=user, is_valid=False, provided_time=provided_created_at, message="Vaqt imzosi yaroqsiz.")
                raise serializers.ValidationError({"signature": "Vaqt imzosi yaroqsiz."})

        if provided_created_at:
            if provided_created_at > timezone.now():
                SignatureLog.objects.create(user=user, is_valid=False, provided_time=provided_created_at, message="Kelajakdagi vaqt.")
                raise serializers.ValidationError({"created_at": "Vaqt kelajakda bo'lishi mumkin emas."})
                
            from datetime import timedelta
            if provided_created_at < timezone.now() - timedelta(hours=24):
                SignatureLog.objects.create(user=user, is_valid=False, provided_time=provided_created_at, message="24 soatdan eskirgan vaqt.")
                raise serializers.ValidationError({"created_at": "Davomat vaqti 24 soatdan eskirgan. Qabul qilinmaydi."})

            SignatureLog.objects.create(user=user, is_valid=True, provided_time=provided_created_at, message="Imzo muvaffaqiyatli tasdiqlandi.")
                
        today = provided_created_at.date() if provided_created_at else timezone.now().date()
        todays_events = Attendance.objects.active().filter(
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
        provided_created_at = validated_data.pop("created_at", None)
        validated_data.pop("signature", None)
        validated_data.pop("image", None)
        validated_data["user"] = self.context["request"].user
        instance = super().create(validated_data)

        if provided_created_at:
            instance.created_at = provided_created_at
            instance.save(update_fields=["created_at"])

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


class FaceLogSerializer(serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)

    class Meta:
        model = FaceLog
        fields = ["id", "user", "user_info", "is_success", "message", "created_at"]


class GpsLogSerializer(serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)

    class Meta:
        model = GpsLog
        fields = ["id", "user", "user_info", "is_success", "latitude", "longitude", "distance_meters", "message", "created_at"]


class SignatureLogSerializer(serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)

    class Meta:
        model = SignatureLog
        fields = ["id", "user", "user_info", "is_valid", "provided_time", "message", "created_at"]

