from unfold.admin import ModelAdmin
from django.contrib import admin

from .models import Attendance, Geozone, FaceLog, GpsLog


@admin.register(Geozone)
class GeozoneAdmin(ModelAdmin):
    list_display = ["name", "zone_type", "branch", "radius", "is_active"]
    search_fields = ["name", "branch__name"]
    list_filter = ["zone_type", "branch"]


@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = ["user", "event_type", "face_verify", "created_at", "is_active"]
    search_fields = ["user__full_name"]
    list_filter = ["event_type", "face_verify", "created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(FaceLog)
class FaceLogAdmin(ModelAdmin):
    list_display = ["user", "is_success", "message", "created_at", "is_active"]
    search_fields = ["user__full_name", "message"]
    list_filter = ["is_success", "created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(GpsLog)
class GpsLogAdmin(ModelAdmin):
    list_display = ["user", "is_success", "distance_meters", "message", "created_at", "is_active"]
    search_fields = ["user__full_name", "message"]
    list_filter = ["is_success", "created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
