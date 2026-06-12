from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta, datetime
from apps.users.models import User
from .models import KPIResult
from .serializers import KPIResultSerializer
from .services import KPIService, DashboardService


@extend_schema(tags=["Analitika va KPI"])
class KPIResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = KPIResult.objects.select_related("user").all()
    serializer_class = KPIResultSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["user", "month", "rating_category"]
    search_fields = ["user__full_name", "user__jshshir"]
    ordering_fields = ["month", "total_score"]
    ordering = ["-month", "-total_score"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.has_permission("analytics_view_all"):
            return super().get_queryset()
        if user.has_permission("analytics_view_dept") and user.department:
            return super().get_queryset().filter(user__department=user.department)
        return super().get_queryset().filter(user=user)

    @extend_schema(
        summary="Xodim uchun ma'lum bir oydagi KPI ni qayta hisoblash",
        parameters=[
            OpenApiParameter(
                name="user_id", description="Xodim UUID", required=True, type=str
            ),
            OpenApiParameter(name="year", description="Yil", required=True, type=int),
            OpenApiParameter(
                name="month", description="Oy (1-12)", required=True, type=int
            ),
        ],
        request=None,
    )
    @action(detail=False, methods=["post"], url_path="calculate-kpi")
    def calculate_kpi(self, request):
        if not (
            request.user.is_superuser
            or request.user.has_permission("analytics_calculate")
        ):
            return Response(
                {"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get("user_id")
        year = request.data.get("year")
        month = request.data.get("month")

        if not all([user_id, year, month]):
            return Response(
                {"detail": "user_id, year va month parametrlari majburiy."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            kpi = KPIService.calculate_user_kpi(target_user, int(year), int(month))
            if kpi:
                return Response(KPIResultSerializer(kpi).data)
            return Response(
                {"detail": "Ushbu oy uchun ish kunlari yo'q."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Umumiy Dashboard Statistikasi",
        parameters=[
            OpenApiParameter(
                name="period",
                description="Filtr (1_day, 1_month, 3_months, 6_months)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="start_date",
                description="Boshlanish sanasi (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="end_date",
                description="Tugash sanasi (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="dashboard-stats")
    def dashboard_stats(self, request):
        period = request.query_params.get("period")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        end_date = timezone.localtime().date()
        start_date = end_date

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        elif period:
            if period == "1_month":
                start_date = end_date - timedelta(days=30)
            elif period == "3_months":
                start_date = end_date - timedelta(days=90)
            elif period == "6_months":
                start_date = end_date - timedelta(days=180)

        stats = DashboardService.get_dashboard_stats(
            request.user, start_date=start_date, end_date=end_date
        )
        if stats is None:
            return Response(
                {"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN
            )

        return Response(stats)
