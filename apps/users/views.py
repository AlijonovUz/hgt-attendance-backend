from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.utils.services import hash_compare
from apps.utils.views import BaseManageViewSet
from apps.utils.throttles import CustomScopedRateThrottle

from .filters import DepartmentFilter, PositionFilter, UserFilter
from .models import Branch, Department, Permission, Position, Role, User
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
)


@extend_schema(tags=["Avtorizatsiya"])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [CustomScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        for throttle in self.get_throttles():
            if hasattr(throttle, 'get_cache_key') and hasattr(throttle, 'cache'):
                if hasattr(throttle, 'scope_attr'):
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
            return Response(
                {
                    "detail": "Foydalanuvchi profilida yuz rasmi mavjud emas. Avval yuz rasm yuklang!"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_verified, msg = hash_compare(user, uploaded_file)

        from apps.attendance.models import FaceLog
        FaceLog.objects.create(
            user=user,
            is_success=is_verified,
            message=msg
        )

        if is_verified:
            return Response(
                {"message": msg, "verified": True}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": msg, "verified": False}, status=status.HTTP_400_BAD_REQUEST
            )


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
        return Response({"detail": "Xodim bloklandi."}, status=status.HTTP_200_OK)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        user = self.get_object()
        if user.is_fired:
            return Response(
                {
                    "detail": "Ishdan bo'shatilgan xodimni blokdan chiqarish mumkin emas!"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()
        return Response(
            {"detail": "Xodim blokdan chiqarildi."}, status=status.HTTP_200_OK
        )

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def fire(self, request, pk=None):
        user = self.get_object()
        user.is_fired = True
        user.is_active = False
        user.save()
        return Response(
            {"detail": "Xodim ishdan bo'shatildi."}, status=status.HTTP_200_OK
        )
