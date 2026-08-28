from django.apps import AppConfig


class MarketConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "market"

    def ready(self):
        import os

        if os.environ.get(
            "RUN_MAIN"
        ) != "true":
            return

        from .scheduler import start

        start()