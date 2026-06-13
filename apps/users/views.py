import logging
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.utils.face import hash_compare
from apps.utils.views import BaseManageViewSet
from apps.utils.throttles import CustomScopedRateThrottle, ThrottleExceptionHandlerMixin

from .filters import DepartmentFilter, PositionFilter, UserFilter
from .models import (
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
from apps.attendance.models import FaceLog
from .serializers import (
    BranchSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    DepartmentSerializer,
    FaceVerificationSerializer,
    PermissionSerializer,
    PositionSerializer,
    ProfileSerializer,
    RoleSerializer,
    UserSerializer,
    WeekDaySerializer,
    HolidaySerializer,
    WorkScheduleSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["Filiallar"])
class BranchViewSet(BaseManageViewSet):
    queryset = Branch.objects.active()
    serializer_class = BranchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["name", "address"]
    action_permissions = {
        "create": "branch_create",
        "update": "branch_edit",
        "partial_update": "branch_edit",
        "destroy": "branch_delete",
    }


@extend_schema(tags=["Bo'limlar"])
class DepartmentViewSet(BaseManageViewSet):
    queryset = Department.objects.select_related("branch").active()
    serializer_class = DepartmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = DepartmentFilter
    search_fields = ["name"]
    action_permissions = {
        "create": "department_create",
        "update": "department_edit",
        "partial_update": "department_edit",
        "destroy": "department_delete",
    }


@extend_schema(tags=["Lavozimlar"])
class PositionViewSet(BaseManageViewSet):
    queryset = Position.objects.select_related(
        "department", "department__branch"
    ).active()
    serializer_class = PositionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = PositionFilter
    search_fields = ["name"]
    action_permissions = {
        "create": "position_create",
        "update": "position_edit",
        "partial_update": "position_edit",
        "destroy": "position_delete",
    }


@extend_schema(tags=["Ruxsatlar"])
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.active()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code"]


@extend_schema(tags=["Rollar"])
class RoleViewSet(BaseManageViewSet):
    queryset = Role.objects.prefetch_related("permissions").active()
    serializer_class = RoleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["name"]
    action_permissions = {
        "create": "role_create",
        "update": "role_edit",
        "partial_update": "role_edit",
        "destroy": "role_delete",
    }


@extend_schema(tags=["Hafta Kunlari"])
class WeekDayViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WeekDay.objects.active().order_by("day_number")
    serializer_class = WeekDaySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


@extend_schema(tags=["Bayramlar"])
class HolidayViewSet(BaseManageViewSet):
    queryset = Holiday.objects.active().order_by("-start_date")
    serializer_class = HolidaySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title"]

    action_permissions = {
        "create": "holiday_create",
        "update": "holiday_edit",
        "partial_update": "holiday_edit",
        "destroy": "holiday_delete",
        "list": "holiday_view",
        "retrieve": "holiday_view",
    }


@extend_schema(tags=["Ish Grafiklari"])
class WorkScheduleViewSet(BaseManageViewSet):
    queryset = WorkSchedule.objects.prefetch_related(
        "mandatory_days", "optional_days"
    ).active()
    serializer_class = WorkScheduleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    action_permissions = {
        "create": "schedule_create",
        "update": "schedule_edit",
        "partial_update": "schedule_edit",
        "destroy": "schedule_delete",
        "list": "schedule_view",
        "retrieve": "schedule_view",
    }


@extend_schema(tags=["Xodimlar"])
class UserViewSet(BaseManageViewSet):
    queryset = User.objects.select_related(
        "branch", "department", "position", "role"
    ).all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = UserFilter
    search_fields = ["full_name", "jshshir", "phone"]

    action_permissions = {
        "list": "employee_view",
        "retrieve": "employee_view",
        "create": "employee_add",
        "update": "employee_edit",
        "partial_update": "employee_edit",
        "fire": "employee_fire",
        "block": "employee_block",
        "unblock": "employee_block",
    }

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed. Use block or fire actions."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()

        logger.warning("Xodim bloklandi: ID=%s, Ism=%s", user.id, user.full_name)
        return Response({"detail": "Xodim bloklandi."}, status=status.HTTP_200_OK)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        user = self.get_object()
        if user.is_fired:
            logger.warning(
                "Bo'shatilgan xodimni blokdan chiqarishga urinish: ID=%s", user.id
            )
            return Response(
                {
                    "detail": "Ishdan bo'shatilgan xodimni blokdan chiqarish mumkin emas!"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()

        logger.info("Xodim blokdan chiqarildi: ID=%s, Ism=%s", user.id, user.full_name)
        return Response(
            {"detail": "Xodim blokdan chiqarildi."}, status=status.HTTP_200_OK
        )

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def fire(self, request, pk=None):
        user = self.get_object()
        user.is_fired = True
        user.is_active = False
        user.fired_at = timezone.now()
        user.save()

        logger.warning(
            "Xodim ishdan bo'shatildi: ID=%s, Ism=%s", user.id, user.full_name
        )
        return Response(
            {"detail": "Xodim ishdan bo'shatildi."}, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Avtorizatsiya"])
class CustomTokenObtainPairView(ThrottleExceptionHandlerMixin, TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [CustomScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            logger.info(
                "Foydalanuvchi tizimga kirdi: %s",
                request.data.get("username", "Noma'lum"),
            )

        for throttle in self.get_throttles():
            if hasattr(throttle, "get_cache_key") and hasattr(throttle, "cache"):
                if hasattr(throttle, "scope_attr"):
                    throttle.scope = getattr(self, throttle.scope_attr, None)
                cache_key = throttle.get_cache_key(request, view=self)
                if cache_key:
                    throttle.cache.delete(cache_key)

        return response


@extend_schema(tags=["Avtorizatsiya"])
class CustomTokenRefreshView(TokenRefreshView):
    pass


@extend_schema(tags=["Profil"])
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Profil"])
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["put"]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            logger.info("Foydalanuvchi parolini o'zgartirdi: ID=%s", request.user.id)
            return Response(
                {"message": "Parol muvaffaqiyatli o'zgartirildi."},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Profil"], request=FaceVerificationSerializer)
class FaceVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = FaceVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["image"]
        user = request.user

        if not user.face_image or not user.face_image.name:
            logger.warning(
                "Yuz tekshiruvi xatosi: Profil rasm yo'q. UserID=%s", user.id
            )
            return Response(
                {
                    "detail": "Foydalanuvchi profilida yuz rasmi mavjud emas. Avval yuz rasm yuklang!"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_verified, msg = hash_compare(user, uploaded_file)

        FaceLog.objects.create(user=user, is_success=is_verified, message=msg)

        if is_verified:
            logger.info("Yuz tekshiruvi MUVAFFAQIYATLI: UserID=%s", user.id)
            return Response(
                {"message": msg, "verified": True}, status=status.HTTP_200_OK
            )
        else:
            logger.warning(
                "Yuz tekshiruvi DIQQAT (Muvaffaqiyatsiz): UserID=%s | Sabab=%s",
                user.id,
                msg,
            )
            return Response(
                {"detail": msg, "verified": False}, status=status.HTTP_400_BAD_REQUEST
            )
