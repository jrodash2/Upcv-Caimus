from django.apps import AppConfig


class AsociacionesAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "asociaciones_app"

    def ready(self):
        import asociaciones_app.signals  # noqa: F401
