import hashlib
from datetime import date
from django.utils import timezone

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.hashers import make_password

from apps.analytics.models import KPIResult
from apps.analytics.services import KPIService
from apps.utils.face import verify_face_image

from .models import (
    Region,
    District,
    Branch,
    Department,
    Permission,
    Position,
    Role,
    User,
    WeekDay,
    Holiday,
    WorkSchedule,
)


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "code", "created_at"]

    @classmethod
    def many_init(cls, *args, **kwargs):
        class GroupedPermissionListSerializer(serializers.ListSerializer):
            def to_representation(self, data):
                iterable = data.all() if hasattr(data, "all") else data
                grouped = {}
                for item in iterable:
                    perm = self.child.to_representation(item)
                    code = perm.get("code", "")
                    module = code.split('_')[0] if '_' in code else 'other'
                    
                    if module == 'attendance':
                        module_key = 'attendances'
                    elif module == 'analytics':
                        module_key = 'analytics'
                    elif not module.endswith('s') and module != 'other':
                        module_key = module + 's'
                    else:
                        module_key = module
                        
                    if module_key not in grouped:
                        grouped[module_key] = []
                    grouped[module_key].append(perm)
                return grouped

            @property
            def data(self):
                ret = super(serializers.ListSerializer, self).data
                from rest_framework.utils.serializer_helpers import ReturnDict
                return ReturnDict(ret, serializer=self)
                
        kwargs['child'] = cls()
        return GroupedPermissionListSerializer(*args, **kwargs)


class RoleShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name", "created_at", "is_active"]


class DistrictSerializer(serializers.ModelSerializer):
    region_info = RegionSerializer(source="region", read_only=True)

    class Meta:
        model = District
        fields = ["id", "name", "region", "region_info", "created_at", "is_active"]
        extra_kwargs = {"region": {"write_only": True}}


class BranchSerializer(serializers.ModelSerializer):
    region_info = RegionSerializer(source="region", read_only=True)
    district_info = DistrictSerializer(source="district", read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "region",
            "district",
            "region_info",
            "district_info",
            "created_at",
            "is_active",
        ]
        extra_kwargs = {
            "region": {"write_only": True},
            "district": {"write_only": True},
        }


class DepartmentShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class PositionShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "name"]


class UserShortInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "face_image"]


class WeekDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeekDay
        fields = ["id", "name", "day_number"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "title", "start_date", "end_date"]


class WorkScheduleShortSerializer(serializers.ModelSerializer):
    mandatory_days_info = WeekDaySerializer(
        source="mandatory_days", read_only=True, many=True
    )
    optional_days_info = WeekDaySerializer(
        source="optional_days", read_only=True, many=True
    )

    class Meta:
        model = WorkSchedule
        fields = [
            "id",
            "name",
            "work_start_time",
            "work_end_time",
            "lunch_start_time",
            "lunch_end_time",
            "mandatory_days_info",
            "optional_days_info",
        ]


class RoleSerializer(serializers.ModelSerializer):
    permissions_info = PermissionSerializer(
        source="permissions", read_only=True, many=True
    )

    class Meta:
        model = Role
        fields = ["id", "name", "permissions_info", "permissions", "created_at"]
        extra_kwargs = {"permissions": {"write_only": True}}


class DepartmentSerializer(serializers.ModelSerializer):
    branch_info = BranchSerializer(source="branch", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "branch_info", "branch", "created_at"]
        extra_kwargs = {"branch": {"write_only": True}}


class PositionSerializer(serializers.ModelSerializer):
    department_info = DepartmentSerializer(source="department", read_only=True)

    class Meta:
        model = Position
        fields = ["id", "name", "department_info", "department", "created_at"]
        extra_kwargs = {"department": {"write_only": True}}


class WorkScheduleSerializer(serializers.ModelSerializer):
    mandatory_days_info = WeekDaySerializer(
        source="mandatory_days", many=True, read_only=True
    )
    optional_days_info = WeekDaySerializer(
        source="optional_days", many=True, read_only=True
    )

    class Meta:
        model = WorkSchedule
        fields = [
            "id",
            "name",
            "work_start_time",
            "work_end_time",
            "lunch_start_time",
            "lunch_end_time",
            "mandatory_days",
            "optional_days",
            "mandatory_days_info",
            "optional_days_info",
        ]
        extra_kwargs = {
            "mandatory_days": {"write_only": True},
            "optional_days": {"write_only": True},
        }


class UserSerializer(serializers.ModelSerializer):
    role_info = RoleShortSerializer(source="role", read_only=True)
    branch_info = BranchSerializer(source="branch", read_only=True)
    department_info = DepartmentShortSerializer(source="department", read_only=True)
    position_info = PositionShortSerializer(source="position", read_only=True)
    schedule_info = WorkScheduleShortSerializer(source="schedule", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "password",
            "jshshir",
            "phone",
            "face_image",
            "branch",
            "branch_info",
            "department",
            "department_info",
            "position",
            "position_info",
            "schedule",
            "schedule_info",
            "role",
            "role_info",
            "is_active",
            "is_fired",
            "fired_at",
            "is_password_changed",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "full_name": {
                "error_messages": {
                    "unique": "Bunday ism-familiyaga ega foydalanuvchi allaqachon mavjud."
                }
            },
            "phone": {
                "error_messages": {
                    "unique": "Bu telefon raqam allaqachon ro'yxatdan o'tgan."
                }
            },
            "jshshir": {
                "error_messages": {
                    "unique": "Bu JShShIR allaqachon ro'yxatdan o'tgan."
                }
            },
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
            "is_fired": {"read_only": True},
            "fired_at": {"read_only": True},
            "is_active": {"read_only": True},
            "is_password_changed": {"read_only": True},
            "role": {"write_only": True},
            "branch": {"write_only": True},
            "department": {"write_only": True},
            "position": {"write_only": True},
            "schedule": {"write_only": True},
        }

    def validate_face_image(self, value):
        if value:
            is_valid, msg = verify_face_image(value)
            if not is_valid:
                raise serializers.ValidationError(msg)
            value.seek(0)
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Parol kamida 8 ta belgidan iborat bo'lishi kerak.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if password:
            validated_data["password"] = make_password(password)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            validated_data["password"] = make_password(password)
        return super().update(instance, validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    current_month_kpi = serializers.SerializerMethodField()
    role_info = RoleShortSerializer(source="role", read_only=True)
    branch_info = BranchSerializer(source="branch", read_only=True)
    department_info = DepartmentShortSerializer(source="department", read_only=True)
    position_info = PositionShortSerializer(source="position", read_only=True)
    schedule_info = WorkScheduleShortSerializer(source="schedule", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "jshshir",
            "phone",
            "face_image",
            "branch_info",
            "department_info",
            "position_info",
            "role_info",
            "schedule_info",
            "current_month_kpi",
            "is_password_changed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "jshshir",
            "current_month_kpi",
            "is_password_changed",
            "created_at",
            "updated_at",
        ]

    def get_current_month_kpi(self, obj):
        now = timezone.localtime()
        current_month = date(now.year, now.month, 1)

        kpi_result = KPIResult.objects.filter(user=obj, month=current_month).first()

        if not kpi_result or kpi_result.updated_at.astimezone().date() < now.date():
            kpi_result = KPIService.calculate_user_kpi(obj, now.year, now.month)

        if not kpi_result:
            return None

        return {
            "total_work_days": kpi_result.total_work_days,
            "attended_days": kpi_result.attended_days,
            "left_early_count": kpi_result.left_early_count,
            "lates_count": kpi_result.lates_count,
            "attendance_kpi": kpi_result.attendance_kpi,
            "monthly_kpi": kpi_result.monthly_kpi,
            "late_coefficient": kpi_result.late_coefficient,
            "discipline_coefficient": kpi_result.discipline_coefficient,
            "total_score": kpi_result.total_score,
            "rating_category": kpi_result.get_rating_category_display()
            if kpi_result.rating_category
            else "Aniqlanmagan",
            "monthly_attendance": f"{kpi_result.attended_days}/{kpi_result.total_work_days}",
        }

    def validate_face_image(self, value):
        if value:
            is_valid, msg = verify_face_image(value)
            if not is_valid:
                raise serializers.ValidationError(msg)
            value.seek(0)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "min_length": "Parol kamida 8 ta raqamdan iborat bo'lishi kerak."
        },
    )

    confirm_new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Eski parol noto'g'ri.")
        return value

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")
        old_password = attrs.get("old_password")

        if new_password != confirm_new_password:
            raise serializers.ValidationError(
                {"new_password": "Yangi parol maydonlari mos kelmadi."}
            )

        if old_password == new_password:
            raise serializers.ValidationError(
                {"new_password": "Yangi parol eskisidan farq qilishi kerak."}
            )

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.is_password_changed = True
        user.save()
        return user


class FaceVerificationSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True, label="Selfie rasm")


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["full_name"] = user.full_name
        token["face_image"] = user.face_image.url if user.face_image else None

        return token

    def validate(self, attrs):
        data: dict = super().validate(attrs)
        user = self.user

        offline_secret = hashlib.sha256(user.password.encode('utf-8')).hexdigest()

        data["user"] = {
            "id": user.id,
            "full_name": user.full_name,
            "face_image": user.face_image.url if user.face_image else None,
            "is_password_changed": user.is_password_changed,
            "offline_secret": offline_secret,
        }

        return data