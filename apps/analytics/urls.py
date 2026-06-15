from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KPIResultViewSet, ReportViewSet

router = DefaultRouter()
router.register(r"kpi", KPIResultViewSet, basename="kpi")
router.register(r"reports", ReportViewSet, basename="reports")

urlpatterns = [
    path("", include(router.urls)),
]
