from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.system.logs.models import AppLog, MailLog

User = get_user_model()

class LogExportTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # Get permissions
        app_log_content_type = ContentType.objects.get_for_model(AppLog)
        mail_log_content_type = ContentType.objects.get_for_model(MailLog)
        
        view_applog_perm = Permission.objects.get(content_type=app_log_content_type, codename='view_applog')
        view_maillog_perm = Permission.objects.get(content_type=mail_log_content_type, codename='view_maillog')
        
        self.user.user_permissions.add(view_applog_perm, view_maillog_perm)
        self.user.save()

        self.client = Client()
        self.client.login(username='testuser', password='password')

        # Create some log data
        AppLog.objects.create(user=self.user, action='test_action', model_name='test_model', object_id='1', object_repr='test_repr')
        MailLog.objects.create(from_email='from@test.com', to_email='to@test.com', subject='test_subject', body='test_body', status='sent')

    def test_app_log_export_csv(self):
        response = self.client.get(reverse('logs:app_log_export') + '?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="app_logs_', response['Content-Disposition'])

    def test_app_log_export_excel(self):
        response = self.client.get(reverse('logs:app_log_export') + '?format=excel')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename="app_logs_', response['Content-Disposition'])

    def test_mail_log_export_csv(self):
        response = self.client.get(reverse('logs:mail_log_export') + '?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="mail_logs_', response['Content-Disposition'])

    def test_mail_log_export_excel(self):
        response = self.client.get(reverse('logs:mail_log_export') + '?format=excel')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename="mail_logs_', response['Content-Disposition'])
