from django.apps import AppConfig

class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.system.useradmin'
    verbose_name = '認証と認可(ログインユーザ)'
