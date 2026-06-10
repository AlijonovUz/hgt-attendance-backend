from rest_framework import viewsets, permissions

class BaseManageViewSet(viewsets.ModelViewSet):
    action_permissions = {}

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]

        class DynamicPermission(permissions.BasePermission):
            def has_permission(self, request, view):
                if not request.user or not request.user.is_authenticated:
                    return False
                
                action_perms = getattr(view, "action_permissions", {})
                perm = action_perms.get(view.action)
                if not perm:
                    return False
                return request.user.has_permission(perm)

        return [DynamicPermission()]
