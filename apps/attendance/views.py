from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters

from apps.utils.views import BaseManageViewSet, BaseReadOnlyViewSet

from .filters import AttendanceFilter, GeozoneFilter
from .models import Attendance, Geozone, FaceLog, GpsLog, SignatureLog
from .serializers import (
    AttendanceCreateSerializer,
    AttendanceListSerializer,
    GeozoneSerializer,
    FaceLogSerializer,
    GpsLogSerializer,
    SignatureLogSerializer,
)


@extend_schema(tags=["Geozonalar"])
class GeozoneViewSet(BaseManageViewSet):
    queryset = Geozone.objects.select_related("branch").active()
    serializer_class = GeozoneSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = GeozoneFilter
    search_fields = ["name"]
    action_permissions = {
        "create": "geozone_create",
        "update": "geozone_edit",
        "partial_update": "geozone_edit",
        "destroy": "geozone_delete",
    }


@extend_schema(tags=["Davomat"])
class AttendanceViewSet(BaseManageViewSet):
    queryset = Attendance.objects.select_related("user").active()
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AttendanceFilter
    search_fields = ["user__full_name", "user__jshshir", "user__phone"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    http_method_names = ["get", "post", "head", "options"]
    action_permissions = {
        "create": "attendance_check_in",
    }

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user

        if user.is_superuser or user.has_permission("attendance_view_history_all"):
            return qs

        if user.has_permission("attendance_view_history_dept") and user.department:
            return qs.filter(Q(user=user) | Q(user__department=user.department))

        return qs.filter(user=user)

    def get_serializer_class(self):
        if self.action == "create":
            return AttendanceCreateSerializer
        return AttendanceListSerializer


@extend_schema(tags=["Face Logs"])
class FaceLogViewSet(BaseReadOnlyViewSet):
    queryset = FaceLog.objects.select_related("user").active()
    serializer_class = FaceLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_success", "user"]
    search_fields = ["user__full_name", "message"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "head", "options"]
    action_permissions = {
        "list": "attendance_view_history_all",
        "retrieve": "attendance_view_history_all",
    }


@extend_schema(tags=["GPS Logs"])
class GpsLogViewSet(BaseReadOnlyViewSet):
    queryset = GpsLog.objects.select_related("user").active()
    serializer_class = GpsLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_success", "user"]
    search_fields = ["user__full_name", "message"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "head", "options"]
    action_permissions = {
        "list": "attendance_view_history_all",
        "retrieve": "attendance_view_history_all",
    }


@extend_schema(tags=["Imzo Loglari"])
class SignatureLogViewSet(BaseReadOnlyViewSet):
    queryset = SignatureLog.objects.select_related("user").active()
    serializer_class = SignatureLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_valid", "user"]
    search_fields = ["user__full_name", "message"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "head", "options"]
    action_permissions = {
        "list": "attendance_view_history_all",
        "retrieve": "attendance_view_history_all",
    }
