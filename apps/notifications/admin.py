from django.contrib import admin
from .models import Notification

from apps.utils.admin import BaseModelAdmin as ModelAdmin


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "title_uz_latn",
        "title_ru",
        "is_read",
        "created_at",
        "is_active",
    )
    list_display_links = ("id", "user")
    list_filter = ("is_read", "created_at")
    search_fields = (
        "user__username",
        "title_uz_latn",
        "message_uz_latn",
        "title_ru",
        "message_ru",
    )
    list_editable = ("is_read",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)

    fieldsets = (
        (
            "Asosiy ma'lumotlar",
            {
                "fields": (
                    "user",
                    "title_uz_latn",
                    "title_uz_cyrl",
                    "title_ru",
                    "message_uz_latn",
                    "message_uz_cyrl",
                    "message_ru",
                )
            },
        ),
        ("Texnik va Holat", {"fields": ("extra_data", "is_read")}),
        (
            "Tizim haqida ma'lumot",
            {
                "fields": ("created_at", "is_active"),
                "classes": ("collapse",),
            },
        ),
    )
