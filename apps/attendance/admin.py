from unfold.admin import ModelAdmin
from django.contrib import admin

from .models import Attendance, Geozone


@admin.register(Geozone)
class GeozoneAdmin(ModelAdmin):
    list_display = ["name", "zone_type", "branch", "radius"]
    search_fields = ["name", "branch__name"]
    list_filter = ["zone_type", "branch"]


@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = ["user", "event_type", "face_verify", "created_at"]
    search_fields = ["user__full_name"]
    list_filter = ["event_type", "face_verify", "created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
