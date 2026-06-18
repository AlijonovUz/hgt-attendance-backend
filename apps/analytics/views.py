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
from .reports import ReportService


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

    def _get_dashboard_params(self, request):
        period = request.query_params.get("period")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        region_id = request.query_params.get("region_id")
        district_id = request.query_params.get("district_id")
        branch_id = request.query_params.get("branch_id")

        end_date = timezone.localtime().date()
        start_date = end_date

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        elif period:
            if period == "daily":
                start_date = end_date
            elif period == "weekly":
                start_date = end_date - timedelta(days=end_date.weekday())
            elif period == "monthly":
                start_date = end_date.replace(day=1)
            elif period == "quarterly":
                start_month = 3 * ((end_date.month - 1) // 3) + 1
                start_date = end_date.replace(month=start_month, day=1)
            elif period == "yearly":
                start_date = end_date.replace(month=1, day=1)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "region_id": region_id,
            "district_id": district_id,
            "branch_id": branch_id
        }



    @extend_schema(
        summary="Dashboard: Asosiy ko'rsatkichlar",
        parameters=[
            OpenApiParameter(name="period", description="Davr (daily, weekly, monthly, quarterly, yearly). Aniq sana yuborilsa buni umuman qo'shmang.", required=False, type=str),
            OpenApiParameter(name="start_date", description="Boshlanish sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="end_date", description="Tugash sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="region_id", description="Viloyat ID", required=False, type=str),
            OpenApiParameter(name="district_id", description="Tuman ID", required=False, type=str),
            OpenApiParameter(name="branch_id", description="Filial ID", required=False, type=str),
        ],
    )
    @action(detail=False, methods=["get"], url_path="dashboard-summary")
    def dashboard_summary(self, request):
        params = self._get_dashboard_params(request)
        stats = DashboardService.get_dashboard_stats(request.user, **params, widgets=["summary"])
        if stats is None:
            return Response({"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)
        return Response(stats["summary"])

    @extend_schema(
        summary="Dashboard: Haftalik dinamika",
        parameters=[
            OpenApiParameter(name="region_id", description="Viloyat ID", required=False, type=str),
            OpenApiParameter(name="district_id", description="Tuman ID", required=False, type=str),
            OpenApiParameter(name="branch_id", description="Filial ID", required=False, type=str),
        ],
    )
    @action(detail=False, methods=["get"], url_path="dashboard-weekly-dynamics")
    def dashboard_weekly_dynamics(self, request):
        params = self._get_dashboard_params(request)
        stats = DashboardService.get_dashboard_stats(request.user, **params, widgets=["weekly_dynamics"])
        if stats is None:
            return Response({"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)
        return Response(stats["weekly_dynamics"])

    @extend_schema(
        summary="Dashboard: Holat bo'yicha taqsimot",
        parameters=[
            OpenApiParameter(name="region_id", description="Viloyat ID", required=False, type=str),
            OpenApiParameter(name="district_id", description="Tuman ID", required=False, type=str),
            OpenApiParameter(name="branch_id", description="Filial ID", required=False, type=str),
        ],
    )
    @action(detail=False, methods=["get"], url_path="dashboard-today-status")
    def dashboard_today_status(self, request):
        params = self._get_dashboard_params(request)
        stats = DashboardService.get_dashboard_stats(request.user, **params, widgets=["today_status"])
        if stats is None:
            return Response({"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)
        return Response(stats["today_status"])

    @extend_schema(
        summary="Dashboard: Intizom reytingi",
        parameters=[
            OpenApiParameter(name="period", description="Davr (daily, weekly, monthly, quarterly, yearly). Aniq sana yuborilsa buni umuman qo'shmang.", required=False, type=str),
            OpenApiParameter(name="start_date", description="Boshlanish sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="end_date", description="Tugash sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="region_id", description="Viloyat ID", required=False, type=str),
            OpenApiParameter(name="district_id", description="Tuman ID", required=False, type=str),
            OpenApiParameter(name="branch_id", description="Filial ID", required=False, type=str),
        ],
    )
    @action(detail=False, methods=["get"], url_path="dashboard-branch-ratings")
    def dashboard_branch_ratings(self, request):
        params = self._get_dashboard_params(request)
        stats = DashboardService.get_dashboard_stats(request.user, **params, widgets=["branch_ratings"])
        if stats is None:
            return Response({"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)
        return Response(stats["branch_ratings"])


@extend_schema(tags=["Hisobotlar"])
class ReportViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Xodimlar bo'yicha hisobot",
        parameters=[
            OpenApiParameter(name="period", description="Davr (daily, weekly, monthly, quarterly, yearly). Aniq sana yuborilsa buni umuman qo'shmang.", required=False, type=str),
            OpenApiParameter(name="start_date", description="Boshlanish sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="end_date", description="Tugash sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="region_id", description="Viloyat ID", required=False, type=str),
            OpenApiParameter(name="district_id", description="Tuman ID", required=False, type=str),
            OpenApiParameter(name="branch_id", description="Filial ID", required=False, type=str),
            OpenApiParameter(name="status", description="Holati (present, absent, late)", required=False, type=str),
        ]
    )
    @action(detail=False, methods=["get"], url_path="by-employee")
    def by_employee(self, request):
        return self._get_report(request, "employee")

    @extend_schema(
        summary="Filiallar bo'yicha hisobot",
        parameters=[
            OpenApiParameter(name="period", description="Davr (daily, weekly, monthly, quarterly, yearly). Aniq sana yuborilsa buni umuman qo'shmang.", required=False, type=str),
            OpenApiParameter(name="start_date", description="Boshlanish sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="end_date", description="Tugash sanasi (YYYY-MM-DD). Agar yuborilsa, period parametrini qo'shmang.", required=False, type=str),
            OpenApiParameter(name="region_id", description="Viloyat ID", required=False, type=str),
            OpenApiParameter(name="district_id", description="Tuman ID", required=False, type=str),
            OpenApiParameter(name="branch_id", description="Filial ID", required=False, type=str),
        ]
    )
    @action(detail=False, methods=["get"], url_path="by-branch")
    def by_branch(self, request):
        return self._get_report(request, "branch")

    def _get_report(self, request, report_type):
        has_access = (
            request.user.is_superuser or 
            request.user.has_permission("report_view_daily") or 
            request.user.has_permission("report_view_weekly") or 
            request.user.has_permission("report_view_monthly")
        )
        if not has_access:
            return Response({"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)
            
        period = request.query_params.get("period")
        start_str = request.query_params.get("start_date")
        end_str = request.query_params.get("end_date")
        
        today = timezone.localtime().date()
        end_date = today
        start_date = today
        
        if start_str and end_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"detail": "Noto'g'ri sana formati."}, status=status.HTTP_400_BAD_REQUEST)
        elif period:
            if period == "daily":
                start_date = end_date
            elif period == "weekly":
                start_date = end_date - timedelta(days=end_date.weekday())
            elif period == "monthly":
                start_date = end_date.replace(day=1)
            elif period == "quarterly":
                start_month = 3 * ((end_date.month - 1) // 3) + 1
                start_date = end_date.replace(month=start_month, day=1)
            elif period == "yearly":
                start_date = end_date.replace(month=1, day=1)
            
        region_id = request.query_params.get("region_id")
        district_id = request.query_params.get("district_id")
        branch_id = request.query_params.get("branch_id")
        status_filter = request.query_params.get("status")

        if report_type == "employee":
            data = ReportService.get_report_by_employee(
                request.user, start_date, end_date,
                region_id=region_id, district_id=district_id, branch_id=branch_id, status=status_filter
            )
        else:
            data = ReportService.get_report_by_branch(
                request.user, start_date, end_date,
                region_id=region_id, district_id=district_id, branch_id=branch_id
            )
            
        return Response(data)
