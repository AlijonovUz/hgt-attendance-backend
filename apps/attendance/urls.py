from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttendanceViewSet, GeozoneViewSet

router = DefaultRouter()
router.register(r"geozones", GeozoneViewSet, basename="geozone")
router.register(r"attendance", AttendanceViewSet, basename="attendance")

urlpatterns = [
    path("", include(router.urls)),
]
