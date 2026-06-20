from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet,
    GeozoneViewSet,
    FaceLogViewSet,
    GpsLogViewSet,
    SignatureLogViewSet,
)

router = DefaultRouter()
router.register(r"geozones", GeozoneViewSet, basename="geozone")
router.register(r"attendance", AttendanceViewSet, basename="attendance")
router.register(r"face-logs", FaceLogViewSet, basename="face-log")
router.register(r"gps-logs", GpsLogViewSet, basename="gps-log")
router.register(r"signature-logs", SignatureLogViewSet, basename="signature-log")

urlpatterns = [
    path("", include(router.urls)),
]
