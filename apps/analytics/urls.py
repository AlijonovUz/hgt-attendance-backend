from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KPIResultViewSet, ReportViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r"kpi", KPIResultViewSet, basename="kpi")
router.register(r"reports", ReportViewSet, basename="reports")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
