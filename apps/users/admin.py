from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import Permission, Role, Branch, Department, Position, User


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["name", "code"]
    search_fields = ["name", "code"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    filter_horizontal = ["permissions"]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "branch"]
    search_fields = ["name", "branch__name"]
    list_filter = ["branch"]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ["name", "department"]
    search_fields = ["name", "department__name"]
    list_filter = ["department"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "full_name",
        "role",
        "branch",
        "department",
        "position",
        "is_active",
        "is_fired",
    ]
    search_fields = ["full_name", "jshshir", "phone"]
    list_filter = ["is_active", "is_fired", "role", "branch", "department", "position"]
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
            "Tashkiliy tuzilma va Ruxsatlar",
            {
                "fields": (
                    "role",
                    "branch",
                    "department",
                    "position",
                    "is_active",
                    "is_fired",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "role", "branch", "department", "position"
        )