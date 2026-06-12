from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.models import User
from .models import KPIResult
from .serializers import KPIResultSerializer
from .services import KPIService, DashboardService


@extend_schema(tags=["Analitika va KPI"])
class KPIResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = KPIResult.objects.select_related("user").all()
    serializer_class = KPIResultSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
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
            OpenApiParameter(name="user_id", description="Xodim UUID", required=True, type=str),
            OpenApiParameter(name="year", description="Yil", required=True, type=int),
            OpenApiParameter(name="month", description="Oy (1-12)", required=True, type=int),
        ],
        request=None
    )
    @action(detail=False, methods=["post"], url_path="calculate-kpi")
    def calculate_kpi(self, request):
        if not (request.user.is_superuser or request.user.has_permission("analytics_calculate")):
            return Response({"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)

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
            return Response({"detail": "Foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        try:
            kpi = KPIService.calculate_user_kpi(target_user, int(year), int(month))
            if kpi:
                return Response(KPIResultSerializer(kpi).data)
            return Response(
                {"detail": "Ushbu oy uchun ish kunlari yo'q."}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Umumiy Dashboard Statistikasi")
    @action(detail=False, methods=["get"], url_path="dashboard-stats")
    def dashboard_stats(self, request):
        stats = DashboardService.get_dashboard_stats(request.user)
        if stats is None:
            return Response({"detail": "Ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)
            
        return Response(stats)
