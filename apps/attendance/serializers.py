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


class GeozoneShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Geozone
        fields = ["id", "name", "zone_type", "latitude", "longitude", "radius"]


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
        fields = [
            "event_type",
            "gps_latitude",
            "gps_longitude",
            "image",
            "created_at",
            "signature",
        ]

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
                raise serializers.ValidationError(
                    {
                        "signature": "Vaqtni tasdiqlash uchun imzo (signature) kiritilishi shart."
                    }
                )

            secret_key = hashlib.sha256(user.password.encode("utf-8")).hexdigest()
            time_str = self.initial_data.get("created_at")

            expected_signature = hmac.new(
                secret_key.encode("utf-8"),
                str(time_str).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, signature):
                SignatureLog.objects.create(
                    user=user,
                    is_valid=False,
                    provided_time=provided_created_at,
                    message="Vaqt imzosi yaroqsiz.",
                )
                raise serializers.ValidationError(
                    {"signature": "Vaqt imzosi yaroqsiz."}
                )

        if provided_created_at:
            if provided_created_at > timezone.now():
                SignatureLog.objects.create(
                    user=user,
                    is_valid=False,
                    provided_time=provided_created_at,
                    message="Kelajakdagi vaqt.",
                )
                raise serializers.ValidationError(
                    {"created_at": "Vaqt kelajakda bo'lishi mumkin emas."}
                )

            from datetime import timedelta

            if provided_created_at < timezone.now() - timedelta(hours=24):
                SignatureLog.objects.create(
                    user=user,
                    is_valid=False,
                    provided_time=provided_created_at,
                    message="24 soatdan eskirgan vaqt.",
                )
                raise serializers.ValidationError(
                    {
                        "created_at": "Davomat vaqti 24 soatdan eskirgan. Qabul qilinmaydi."
                    }
                )

            SignatureLog.objects.create(
                user=user,
                is_valid=True,
                provided_time=provided_created_at,
                message="Imzo muvaffaqiyatli tasdiqlandi.",
            )

        today = (
            provided_created_at.date() if provided_created_at else timezone.now().date()
        )
        todays_events = (
            Attendance.objects.active()
            .filter(user=user, created_at__date=today)
            .values_list("event_type", flat=True)
        )

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
        closest_geozone = None
        for gz in user_geozones:
            distance = haversine(
                float(lat), float(lon), float(gz.latitude), float(gz.longitude)
            )
            if distance < min_distance:
                min_distance = distance
                closest_geozone = gz
            if distance <= float(gz.radius):
                in_geozone = True
                closest_geozone = gz
                break

        GpsLog.objects.create(
            user=user,
            geozone=closest_geozone,
            is_success=in_geozone,
            latitude=lat,
            longitude=lon,
            distance_meters=min_distance if min_distance != float("inf") else None,
            message="Ichida" if in_geozone else "Tashqarida",
        )

        if not in_geozone:
            Notification.objects.create(
                user=user,
                title_uz_latn="Geozonadan tashqarida qayd etildi",
                title_uz_cyrl="Геозонадан ташқарида қайд этилди",
                title_ru="Зафиксировано вне геозоны",
                message_uz_latn="Siz ish joyi geozonasidan tashqarida davomat qayd etdingiz.",
                message_uz_cyrl="Сиз иш жойи геозонасидан ташқарида давомат қайд этдингиз.",
                message_ru="Вы отметили посещаемость вне геозоны вашего рабочего места.",
                extra_data={"event": "OUT_OF_ZONE"},
            )

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
                title_uz_latn="Kechikish",
                title_uz_cyrl="Кечикиш",
                title_ru="Опоздание",
                message_uz_latn=f"Siz bugun ishga kechikib keldingiz. (Belgilangan vaqt: {st.strftime('%H:%M')})",
                message_uz_cyrl=f"Сиз бугун ишга кечикиб келдингиз. (Белгиланган вақт: {st.strftime('%H:%M')})",
                message_ru=f"Вы сегодня опоздали на работу. (Установленное время: {st.strftime('%H:%M')})",
                extra_data={"event": "LATE_CHECK_IN"},
            )
        elif (
            event == Attendance.EventType.LUNCH_END
            and let is not None
            and current_time > let
        ):
            Notification.objects.create(
                user=user,
                title_uz_latn="Tushlikdan kechikish",
                title_uz_cyrl="Тушликдан кечикиш",
                title_ru="Опоздание с обеда",
                message_uz_latn=f"Siz tushlikdan kech qaytdingiz. (Belgilangan vaqt: {let.strftime('%H:%M')})",
                message_uz_cyrl=f"Сиз тушликдан кеч қайтдингиз. (Белгиланган вақт: {let.strftime('%H:%M')})",
                message_ru=f"Вы опоздали с обеденного перерыва. (Установленное время: {let.strftime('%H:%M')})",
                extra_data={"event": "LATE_LUNCH_RETURN"},
            )
        elif event == Attendance.EventType.CHECK_OUT and current_time < et:
            Notification.objects.create(
                user=user,
                title_uz_latn="Erta ketish",
                title_uz_cyrl="Эрта кетиш",
                title_ru="Ранний уход",
                message_uz_latn=f"Siz ish vaqti tugamasdan oldin ketdingiz. (Belgilangan vaqt: {et.strftime('%H:%M')})",
                message_uz_cyrl=f"Сиз иш вақти тугамасдан олдин кетдингиз. (Белгиланган вақт: {et.strftime('%H:%M')})",
                message_ru=f"Вы ушли до окончания рабочего времени. (Установленное время: {et.strftime('%H:%M')})",
                extra_data={"event": "EARLY_CHECK_OUT"},
            )

        from apps.analytics.tasks import update_kpi_for_user_task

        dt = timezone.localtime(instance.created_at)
        update_kpi_for_user_task.delay(user.id, dt.year, dt.month)

        return instance


class RegionDistrictBranchMixin(serializers.Serializer):
    region = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    branch = serializers.SerializerMethodField()

    def get_region(self, obj):
        if obj.user and getattr(obj.user, "branch", None) and obj.user.branch.region:
            return {
                "id": obj.user.branch.region.id,
                "name": obj.user.branch.region.name,
            }
        return None

    def get_district(self, obj):
        if obj.user and getattr(obj.user, "branch", None) and obj.user.branch.district:
            return {
                "id": obj.user.branch.district.id,
                "name": obj.user.branch.district.name,
            }
        return None

    def get_branch(self, obj):
        if obj.user and getattr(obj.user, "branch", None):
            return {"id": obj.user.branch.id, "name": obj.user.branch.name}
        return None


class FaceLogSerializer(RegionDistrictBranchMixin, serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)

    class Meta:
        model = FaceLog
        fields = [
            "id",
            "user",
            "user_info",
            "region",
            "district",
            "branch",
            "is_success",
            "message",
            "created_at",
        ]


class GpsLogSerializer(RegionDistrictBranchMixin, serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)
    geozone_info = GeozoneShortSerializer(source="geozone", read_only=True)

    class Meta:
        model = GpsLog
        fields = [
            "id",
            "user",
            "user_info",
            "region",
            "district",
            "branch",
            "geozone_info",
            "is_success",
            "latitude",
            "longitude",
            "distance_meters",
            "message",
            "created_at",
        ]


class SignatureLogSerializer(RegionDistrictBranchMixin, serializers.ModelSerializer):
    user_info = UserShortInfoSerializer(source="user", read_only=True)

    class Meta:
        model = SignatureLog
        fields = [
            "id",
            "user",
            "user_info",
            "region",
            "district",
            "branch",
            "is_valid",
            "provided_time",
            "message",
            "created_at",
        ]
