from unfold.admin import ModelAdmin


class BaseModelAdmin(ModelAdmin):
    def delete_model(self, request, obj):
        if hasattr(obj, "hard_delete"):
            obj.hard_delete()
        else:
            obj.delete()

    def delete_queryset(self, request, queryset):
        if hasattr(queryset, "hard_delete"):
            queryset.hard_delete()
        else:
            queryset.delete()
