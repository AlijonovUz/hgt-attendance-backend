from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from apps.utils.services import hash_compare

from apps.users.models import Branch, Department, Permission, Position, Role, User
from apps.users.serializers import (
    BranchSerializer,
    CustomTokenObtainPairSerializer,
    DepartmentSerializer,
    PermissionSerializer,
    PositionSerializer,
    RoleSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    ProfileSerializer,
    FaceVerificationSerializer,
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
    search_fields = ["full_name", "jshshir", "phone"]

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
                {"detail": "Ishdan bo'shatilgan xodimni blokdan chiqarish mumkin emas!"},
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


@extend_schema(tags=["Profile"])
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Profile"], request=FaceVerificationSerializer)
class FaceVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = FaceVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["image"]
        user = request.user

        if not user.face_image or not user.face_image.name:
            return Response(
                {"detail": "Foydalanuvchi profilida yuz rasmi mavjud emas. Avval yuz rasm yuklang!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_verified, msg = hash_compare(user, uploaded_file)
        
        if is_verified:
            return Response({"message": msg, "verified": True}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": msg, "verified": False}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Profile"])
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['put']

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Parol muvaffaqiyatli o'zgartirildi."
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Ruxsatlar (Permissions)"])
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.active()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(tags=["Rollar (Roles)"])
class RoleViewSet(BaseManageViewSet):
    queryset = Role.objects.active()
    serializer_class = RoleSerializer
    action_permissions = {
        "create": "role_create",
        "update": "role_edit",
        "partial_update": "role_edit",
        "destroy": "role_delete",
    }


@extend_schema(tags=["Filiallar (Branches)"])
class BranchViewSet(BaseManageViewSet):
    queryset = Branch.objects.active()
    serializer_class = BranchSerializer
    action_permissions = {
        "create": "branch_create",
        "update": "branch_edit",
        "partial_update": "branch_edit",
        "destroy": "branch_delete",
    }


@extend_schema(tags=["Bo'limlar (Departments)"])
class DepartmentViewSet(BaseManageViewSet):
    queryset = Department.objects.active()
    serializer_class = DepartmentSerializer
    action_permissions = {
        "create": "department_create",
        "update": "department_edit",
        "partial_update": "department_edit",
        "destroy": "department_delete",
    }


@extend_schema(tags=["Lavozimlar (Positions)"])
class PositionViewSet(BaseManageViewSet):
    queryset = Position.objects.active()
    serializer_class = PositionSerializer
    action_permissions = {
        "create": "position_create",
        "update": "position_edit",
        "partial_update": "position_edit",
        "destroy": "position_delete",
    }
