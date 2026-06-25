from django.urls import path
from .views import telegram_webhook_view

urlpatterns = [
    path("webhook/", telegram_webhook_view, name="telegram_webhook"),
]
