from django.test.runner import DiscoverRunner
from django.db.models.signals import post_save, post_delete
from apps.common.signals import log_save, log_delete

class CustomTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        # Disconnect signals before database setup
        post_save.disconnect(log_save)
        post_delete.disconnect(log_delete)

        # Call the super method to set up databases
        result = super().setup_databases(**kwargs)

        # Reconnect signals after database setup
        post_save.connect(log_save)
        post_delete.connect(log_delete)

        return result
