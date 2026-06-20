from datetime import datetime
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.utils.views import BaseManageViewSet, BaseReadOnlyViewSet
from apps.attendance.services import AttendanceService

from .filters import (
    AttendanceFilter,
    GeozoneFilter,
    FaceLogFilter,
    GpsLogFilter,
    SignatureLogFilter,
)
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

        if user.has_permission("attendance_view_history_self"):
            return qs.filter(user=user)

        return qs.none()

    def get_serializer_class(self):
        if self.action == "create":
            return AttendanceCreateSerializer
        return AttendanceListSerializer

    @extend_schema(
        summary="Shaxsiy davomat statistikasi",
        parameters=[
            OpenApiParameter(
                "start_date",
                type=str,
                required=False,
                description="Boshlanish sanasi (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                "end_date",
                type=str,
                required=False,
                description="Tugash sanasi (YYYY-MM-DD)",
            ),
        ],
        responses={
            200: inline_serializer(
                name="PersonalStats",
                fields={
                    "present_days": serializers.IntegerField(),
                    "late_days": serializers.IntegerField(),
                    "avg_check_in": serializers.CharField(),
                    "total_worked_hours": serializers.IntegerField(),
                },
            )
        },
    )
    @action(detail=False, methods=["get"], url_path="personal-stats")
    def personal_stats(self, request):
        user = request.user

        start_str = request.query_params.get("start_date")
        end_str = request.query_params.get("end_date")

        today = timezone.localtime().date()
        start_date = today.replace(day=1)
        end_date = today

        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"detail": "start_date noto'g'ri formatda (YYYY-MM-DD)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if end_str:
            try:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"detail": "end_date noto'g'ri formatda (YYYY-MM-DD)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if start_date > end_date:
            return Response(
                {"detail": "start_date end_date dan katta bo'lishi mumkin emas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = AttendanceService.get_personal_stats(user, start_date, end_date)
        return Response(data)


@extend_schema(tags=["Face Logs"])
class FaceLogViewSet(BaseReadOnlyViewSet):
    queryset = FaceLog.objects.select_related(
        "user", "user__branch", "user__branch__region", "user__branch__district"
    ).active()
    serializer_class = FaceLogSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = FaceLogFilter
    search_fields = ["user__full_name", "message"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "head", "options"]
    action_permissions = {
        "list": "log_view_face",
        "retrieve": "log_view_face",
    }


@extend_schema(tags=["GPS Logs"])
class GpsLogViewSet(BaseReadOnlyViewSet):
    queryset = GpsLog.objects.select_related(
        "user",
        "user__branch",
        "user__branch__region",
        "user__branch__district",
        "geozone",
    ).active()
    serializer_class = GpsLogSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = GpsLogFilter
    search_fields = ["user__full_name", "message"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "head", "options"]
    action_permissions = {
        "list": "log_view_gps",
        "retrieve": "log_view_gps",
    }


@extend_schema(tags=["Imzo Loglari"])
class SignatureLogViewSet(BaseReadOnlyViewSet):
    queryset = SignatureLog.objects.select_related(
        "user", "user__branch", "user__branch__region", "user__branch__district"
    ).active()
    serializer_class = SignatureLogSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = SignatureLogFilter
    search_fields = ["user__full_name", "message"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "head", "options"]
    action_permissions = {
        "list": "log_view_signature",
        "retrieve": "log_view_signature",
    }
