from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    name = "apps.analytics"

    def ready(self):
        import apps.analytics.signals
