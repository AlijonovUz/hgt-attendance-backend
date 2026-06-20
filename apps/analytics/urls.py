from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    KPIResultViewSet,
    ReportViewSet,
    DashboardViewSet,
    DailyAttendanceViewSet,
)

router = DefaultRouter()
router.register(r"kpi", KPIResultViewSet, basename="kpi")
router.register(
    r"daily-attendance", DailyAttendanceViewSet, basename="daily-attendance"
)
router.register(r"reports", ReportViewSet, basename="reports")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
