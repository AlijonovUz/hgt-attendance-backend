from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.utils.services import verify_face_image

from .models import Branch, Department, Permission, Position, Role, User


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "code", "created_at"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "permissions", "created_at"]


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "created_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "branch", "created_at"]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "name", "department", "created_at"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["full_name"] = user.full_name
        token["role"] = user.role.name if user.role else None

        if user.role:
            token["permissions"] = list(
                user.role.permissions.values_list("code", flat=True)
            )
        else:
            token["permissions"] = []

        return token


class UserSerializer(serializers.ModelSerializer):
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
            "department",
            "position",
            "role",
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
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    current_month_kpi = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "jshshir",
            "phone",
            "face_image",
            "branch",
            "department",
            "position",
            "role",
            "current_month_kpi",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "jshshir",
            "branch",
            "department",
            "position",
            "role",
            "current_month_kpi",
            "created_at",
            "updated_at",
        ]

    def get_current_month_kpi(self, obj):
        from datetime import date
        from django.utils import timezone
        from apps.analytics.models import KPIResult
        from apps.analytics.services import calculate_user_kpi

        now = timezone.localtime()
        current_month = date(now.year, now.month, 1)

        kpi_result = KPIResult.objects.filter(user=obj, month=current_month).first()

        if not kpi_result or kpi_result.updated_at.astimezone().date() < now.date():
            kpi_result = calculate_user_kpi(obj, now.year, now.month)

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
