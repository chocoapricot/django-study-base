from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.system.logs'
    verbose_name = 'システムログ'
    
    def ready(self):
        """アプリ準備完了時にシグナルを登録"""
        import apps.system.logs.signals