from rest_framework import viewsets, permissions
from django.core.exceptions import ImproperlyConfigured

class BaseManageViewSet(viewsets.ModelViewSet):
    permission_code = None
    action_permissions = {}

    def get_permissions(self):
        if self.permission_code and self.action_permissions:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} da ham 'permission_code', ham 'action_permissions' berilgan. "
                "Iltimos, faqat bittasidan foydalaning!"
            )

        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]

        class DynamicPermission(permissions.BasePermission):
            def has_permission(self, request, view):
                if not request.user or not request.user.is_authenticated:
                    return False
                
                action_perms = getattr(view, "action_permissions", {})
                if action_perms:
                    perm = action_perms.get(view.action)
                    if not perm:
                        return False
                    return request.user.has_permission(perm)

                if not view.permission_code:
                    return True
                return request.user.has_permission(view.permission_code)

        return [DynamicPermission()]
