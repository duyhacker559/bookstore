from django.apps import AppConfig

class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    def ready(self):
        # Register signal handlers (no DB access at import/startup time).
        import store.signals  # noqa: F401
