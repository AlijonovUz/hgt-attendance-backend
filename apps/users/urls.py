from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    UserViewSet,
    PermissionViewSet,
    RoleViewSet,
    BranchViewSet,
    DepartmentViewSet,
    PositionViewSet,
)

router = DefaultRouter()
router.register(r"employees", UserViewSet, basename="employees")
router.register(r"permissions", PermissionViewSet, basename="permissions")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"branches", BranchViewSet, basename="branches")
router.register(r"departments", DepartmentViewSet, basename="departments")
router.register(r"positions", PositionViewSet, basename="positions")

urlpatterns = [
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
