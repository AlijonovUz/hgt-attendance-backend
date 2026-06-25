from django.contrib import admin
from apps.utils.admin import BaseModelAdmin as ModelAdmin

from .models import (
    Region,
    District,
    Branch,
    Department,
    Permission,
    Position,
    Role,
    User,
    WeekDay,
    Holiday,
    WorkSchedule,
)


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ["name", "code", "is_active"]
    search_fields = ["name", "code"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]
    filter_horizontal = ["permissions"]


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]


@admin.register(District)
class DistrictAdmin(ModelAdmin):
    list_display = ["name", "region", "is_active"]
    search_fields = ["name", "region__name"]
    list_filter = ["region"]


@admin.register(Branch)
class BranchAdmin(ModelAdmin):
    list_display = ["name", "region", "district", "is_active"]
    search_fields = ["name", "region__name", "district__name"]
    list_filter = ["region", "district"]


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ["name", "branch", "is_active"]
    search_fields = ["name", "branch__name"]
    list_filter = ["branch"]


@admin.register(Position)
class PositionAdmin(ModelAdmin):
    list_display = ["name", "department", "is_active"]
    search_fields = ["name", "department__name"]
    list_filter = ["department"]


@admin.register(WeekDay)
class WeekDayAdmin(ModelAdmin):
    list_display = ["name", "day_number", "is_active"]
    ordering = ["day_number"]


@admin.register(Holiday)
class HolidayAdmin(ModelAdmin):
    list_display = ["title", "start_date", "end_date", "is_active"]
    search_fields = ["title"]
    ordering = ["-start_date"]


@admin.register(WorkSchedule)
class WorkScheduleAdmin(ModelAdmin):
    list_display = [
        "name",
        "work_start_time",
        "work_end_time",
        "lunch_start_time",
        "lunch_end_time",
        "is_active",
    ]
    search_fields = ["name"]
    filter_horizontal = ["mandatory_days", "optional_days"]


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = [
        "full_name",
        "role",
        "branch",
        "department",
        "position",
        "schedule",
        "is_active",
        "is_fired",
        "telegram_id",
        "language",
    ]
    search_fields = ["full_name", "jshshir", "phone", "telegram_id"]
    list_filter = [
        "is_active",
        "is_fired",
        "role",
        "branch",
        "department",
        "position",
        "schedule",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("full_name", "password")}),
        (
            "Shaxsiy ma'lumotlar",
            {
                "fields": (
                    "jshshir",
                    "phone",
                    "face_image",
                )
            },
        ),
        (
            "Telegram sozlamalari",
            {
                "fields": (
                    "telegram_id",
                    "language",
                )
            },
        ),
        (
            "Tashkiliy tuzilma va Ruxsatlar",
            {
                "fields": (
                    "role",
                    "branch",
                    "department",
                    "position",
                    "schedule",
                    "is_active",
                    "is_fired",
                    "fired_at",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("role", "branch", "department", "position", "schedule")
        )

    def save_model(self, request, obj, form, change):
        if obj.password and not obj.password.startswith("pbkdf2_"):
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)
