from django.urls import include, path

urlpatterns = [
    path("users/", include("apps.users.urls")),
    path("attendance/", include("apps.attendance.urls")),
    path("audit/", include("apps.audit.urls")),
    path("notifications/", include("apps.notifications.urls")),
]
