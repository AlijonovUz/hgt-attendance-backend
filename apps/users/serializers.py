from datetime import date
from django.utils import timezone

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.analytics.models import KPIResult
from apps.analytics.services import KPIService
from apps.utils.services import verify_face_image

from .models import Branch, Department, Permission, Position, Role, User


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "code", "created_at"]


class RoleShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class RoleSerializer(serializers.ModelSerializer):
    permissions_info = PermissionSerializer(source="permissions", read_only=True, many=True)

    class Meta:
        model = Role
        fields = ["id", "name", "permissions_info", "permissions", "created_at"]
        extra_kwargs = {
            "permissions": {"write_only": True}
        }


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "created_at"]


class DepartmentShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    branch_info = BranchSerializer(source="branch", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "branch_info", "branch", "created_at"]
        extra_kwargs = {
            "branch": {"write_only": True}
        }


class PositionShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "name"]


class PositionSerializer(serializers.ModelSerializer):
    department_info = DepartmentSerializer(source="department", read_only=True)

    class Meta:
        model = Position
        fields = ["id", "name", "department_info", "department", "created_at"]
        extra_kwargs = {
            "department": {"write_only": True}
        }


class UserShortInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "face_image"]


class UserSerializer(serializers.ModelSerializer):
    role_info = RoleShortSerializer(source="role", read_only=True)
    branch_info = BranchSerializer(source="branch", read_only=True)
    department_info = DepartmentShortSerializer(source="department", read_only=True)
    position_info = PositionShortSerializer(source="position", read_only=True)

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
            "role",
            "role_info",
            "is_active",
            "is_fired",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
            "is_fired": {"read_only": True},
            "is_active": {"read_only": True},
            "role": {"write_only": True},
            "branch": {"write_only": True},
            "department": {"write_only": True},
            "position": {"write_only": True},
        }

    def validate_face_image(self, value):
        if value:
            is_valid, msg = verify_face_image(value)
            if not is_valid:
                raise serializers.ValidationError(msg)
            value.seek(0)
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if password:
            from django.contrib.auth.hashers import make_password
            validated_data["password"] = make_password(password)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            from django.contrib.auth.hashers import make_password
            validated_data["password"] = make_password(password)
        return super().update(instance, validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    current_month_kpi = serializers.SerializerMethodField()
    role_info = RoleShortSerializer(source="role", read_only=True)
    branch_info = BranchSerializer(source="branch", read_only=True)
    department_info = DepartmentShortSerializer(source="department", read_only=True)
    position_info = PositionShortSerializer(source="position", read_only=True)

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
            "current_month_kpi",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "jshshir",
            "current_month_kpi",
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
            "attendance_kpi": kpi_result.attendance_kpi,
            "monthly_kpi": kpi_result.monthly_kpi,
            "late_coefficient": kpi_result.late_coefficient,
            "discipline_coefficient": kpi_result.discipline_coefficient,
            "total_score": kpi_result.total_score,
            "rating_category": kpi_result.get_rating_category_display(),
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

        try:
            validate_password(new_password, self.context["request"].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

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
        user.change_password = False
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

        data["user"] = {
            "id": user.id,
            "full_name": user.full_name,
            "face_image": user.face_image.url if user.face_image else None,
        }

        return data
