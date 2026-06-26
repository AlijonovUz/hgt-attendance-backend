from rest_framework import permissions, viewsets


class BaseManageViewSet(viewsets.ModelViewSet):
    """
    CRUD amallari uchun bazaviy ViewSet. action_permissions lug'ati (dict) yordamida 
    har bir metod uchun qaysi ruxsat talab qilinishini dinamik ravishda tekshiradi.
    """
    action_permissions = {}

    def get_permissions(self):
        class DynamicPermission(permissions.BasePermission):
            def has_permission(self, request, view):
                if not request.user or not request.user.is_authenticated:
                    return False

                action_perms = getattr(view, "action_permissions", {})
                perm = action_perms.get(view.action)

                if not perm:
                    if view.action in ["list", "retrieve"]:
                        return True
                    return False

                return request.user.has_permission(perm)

        return [DynamicPermission()]


class BaseReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Faqat o'qish amallari (List, Retrieve) uchun mo'ljallangan bazaviy ViewSet. 
    Bu ham action_permissions orqali huquqlarni tekshiradi.
    """
    action_permissions = {}

    def get_permissions(self):
        class DynamicPermission(permissions.BasePermission):
            def has_permission(self, request, view):
                if not request.user or not request.user.is_authenticated:
                    return False

                action_perms = getattr(view, "action_permissions", {})
                perm = action_perms.get(view.action)

                if not perm:
                    if view.action in ["list", "retrieve"]:
                        return True
                    return False

                return request.user.has_permission(perm)

        return [DynamicPermission()]
