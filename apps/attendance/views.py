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
    """
    Ish joylari (Geozonalar) ni yaratish, tahrirlash va o'chirish uchun mas'ul API.
    Faqatgina tegishli huquqi bor xodimlar boshqara oladi.
    """
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
    """
    Xodimlarning davomatlarini qayd etish (Kelish/Ketish) va tarixini ko'rish uchun mo'ljallangan API.
    Shuningdek xodimning shaxsiy statistikasini ham hisoblab qaytaradi.
    """
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
        "personal_stats": "attendance_view_history_self",
    }

    def get_queryset(self):
        """
        So'rov yuborgan foydalanuvchining huquqlariga qarab bazadagi yozuvlarni filtrlaydi.
        Masalan:
        - Superadmin barchasini ko'radi.
        - Viloyat yoki tuman filiali rahbari faqat o'ziga tegishlilarini ko'radi.
        - Oddiy xodim esa faqat o'z davomatini ko'radi.
        """
        qs = self.queryset
        user = self.request.user

        if user.is_superuser or user.has_permission("attendance_view_history_all"):
            return qs

        if (
            user.has_permission("attendance_view_history_region")
            and user.branch
            and user.branch.region_id
        ):
            return qs.filter(user__branch__region_id=user.branch.region_id)

        if (
            user.has_permission("attendance_view_history_district")
            and user.branch
            and user.branch.district_id
        ):
            return qs.filter(user__branch__district_id=user.branch.district_id)

        if user.has_permission("attendance_view_history_branch") and user.branch_id:
            return qs.filter(user__branch_id=user.branch_id)

        if user.has_permission("attendance_view_history_dept") and user.department_id:
            return qs.filter(Q(user=user) | Q(user__department_id=user.department_id))

        if user.has_permission("attendance_view_history_self"):
            return qs.filter(user=user)

        return qs.none()

    def get_serializer_class(self):
        """Amalga (yozish yoki o'qish) qarab to'g'ri Serializer ni tanlaydi."""
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
        """
        Xodimning joriy yoki tanlangan oydagi shaxsiy statistikasini hisoblaydi:
        - Jami ishlagan soatlari.
        - Kechikkan kunlari.
        - O'rtacha kelish vaqti.
        """
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
    """
    Yuzni tekshirish tizimidagi urinishlar ro'yxatini (Logs) ko'rsatish API'si.
    """
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
    """
    Foydalanuvchilar qayerda turib davomat qayd etgani (Geozonaga tushgan yoki yo'q) haqida
    hisobot qaytarish API'si.
    """
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
    """
    Oflayn ishlash rejimida telefon tomonidan yaratilgan vaqt imzolari
    qanchalik haqiqiy ekanligini kuzatib boruvchi Logs API'si.
    """
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
