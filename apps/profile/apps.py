from django.apps import AppConfig


class ProfileConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.profile'
    verbose_name = 'プロフィール'

    def ready(self):
        import apps.profile.signals