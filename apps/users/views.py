from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.models import Branch, Department, Permission, Position, Role, User
from apps.users.serializers import (
    BranchSerializer,
    CustomTokenObtainPairSerializer,
    DepartmentSerializer,
    PermissionSerializer,
    PositionSerializer,
    RoleSerializer,
    UserSerializer,
)
from apps.utils.views import BaseManageViewSet


@extend_schema(tags=["Auth"])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(tags=["Auth"])
class CustomTokenRefreshView(TokenRefreshView):
    pass


@extend_schema(tags=["Xodimlar (Employees)"])
class UserViewSet(BaseManageViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        "is_active",
        "is_fired",
        "branch",
        "department",
        "position",
        "role",
    ]
    search_fields = ["full_name", "username", "jshshir", "phone"]

    action_permissions = {
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

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({"detail": "Xodim bloklandi."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        user = self.get_object()
        if user.is_fired:
            return Response(
                {"detail": "Ishdan bo'shatilgan xodimni blokdan chiqarish mumkin emas!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()
        return Response(
            {"detail": "Xodim blokdan chiqarildi."}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def fire(self, request, pk=None):
        user = self.get_object()
        user.is_fired = True
        user.is_active = False
        user.save()
        return Response(
            {"detail": "Xodim ishdan bo'shatildi."}, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Ruxsatlar (Permissions)"])
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.active()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(tags=["Rollar (Roles)"])
class RoleViewSet(BaseManageViewSet):
    queryset = Role.objects.active()
    serializer_class = RoleSerializer
    permission_code = "role_manage"


@extend_schema(tags=["Filiallar (Branches)"])
class BranchViewSet(BaseManageViewSet):
    queryset = Branch.objects.active()
    serializer_class = BranchSerializer
    permission_code = "branch_manage"


@extend_schema(tags=["Bo'limlar (Departments)"])
class DepartmentViewSet(BaseManageViewSet):
    queryset = Department.objects.active()
    serializer_class = DepartmentSerializer
    permission_code = "department_manage"


@extend_schema(tags=["Lavozimlar (Positions)"])
class PositionViewSet(BaseManageViewSet):
    queryset = Position.objects.active()
    serializer_class = PositionSerializer
    permission_code = "position_manage"
