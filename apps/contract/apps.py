from django.apps import AppConfig


class ContractConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contract'
    verbose_name = '契約管理'

    def ready(self):
        import apps.contract.signals
