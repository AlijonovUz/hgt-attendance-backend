from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BranchViewSet,
    ChangePasswordView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    DepartmentViewSet,
    FaceVerificationView,
    PermissionViewSet,
    PositionViewSet,
    ProfileView,
    RoleViewSet,
    UserViewSet,
    WeekDayViewSet,
    HolidayViewSet,
    WorkScheduleViewSet,
)

router = DefaultRouter()
router.register(r"employees", UserViewSet, basename="employees")
router.register(r"permissions", PermissionViewSet, basename="permissions")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"branches", BranchViewSet, basename="branches")
router.register(r"departments", DepartmentViewSet, basename="departments")
router.register(r"positions", PositionViewSet, basename="positions")
router.register(r"weekdays", WeekDayViewSet, basename="weekdays")
router.register(r"holidays", HolidayViewSet, basename="holidays")
router.register(r"schedules", WorkScheduleViewSet, basename="schedules")

urlpatterns = [
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/profile/", ProfileView.as_view(), name="profile"),
    path("auth/verify-face/", FaceVerificationView.as_view(), name="verify_face"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("", include(router.urls)),
]
