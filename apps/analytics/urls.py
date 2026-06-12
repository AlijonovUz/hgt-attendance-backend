from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KPIResultViewSet

router = DefaultRouter()
router.register(r"kpi", KPIResultViewSet, basename="kpi")

urlpatterns = [
    path("", include(router.urls)),
]
