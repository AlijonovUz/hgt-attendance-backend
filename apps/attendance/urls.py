from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttendanceViewSet, GeozoneViewSet, FaceLogViewSet, GpsLogViewSet

router = DefaultRouter()
router.register(r"geozones", GeozoneViewSet, basename="geozone")
router.register(r"attendance", AttendanceViewSet, basename="attendance")
router.register(r"face-logs", FaceLogViewSet, basename="face-log")
router.register(r"gps-logs", GpsLogViewSet, basename="gps-log")

urlpatterns = [
    path("", include(router.urls)),
]
