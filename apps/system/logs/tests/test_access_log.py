from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from apps.system.logs.models import AccessLog
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff

User = get_user_model()

class AccessLogViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='password')
        cls.group, _ = Group.objects.get_or_create(name='testgroup')

        content_type = ContentType.objects.get_for_model(AccessLog)
        try:
            permission = Permission.objects.get(
                codename='view_accesslog',
                content_type=content_type,
            )
            cls.group.permissions.add(permission)
        except Permission.DoesNotExist:
            pass
        cls.user.groups.add(cls.group)

    def setUp(self):
        self.client.login(username='testuser', password='password')
        AccessLog.objects.all().delete()
        # Create dummy staff objects for reversing detail URL
        self.s1 = Staff.objects.create(name='staff1')
        self.s2 = Staff.objects.create(name='staff2')

    def test_access_log_aggregation_and_display(self):
        """
        Test that different URLs are correctly aggregated under a single clean pattern.
        """
        # Manually create logs before accessing the view
        AccessLog.objects.create(url='/', user=self.user)
        AccessLog.objects.create(url='/staff/', user=self.user)
        AccessLog.objects.create(url='/staff/staff/detail/1/', user=self.user)
        AccessLog.objects.create(url='/staff/staff/detail/2/', user=self.user)

        # Access the log view page
        response = self.client.get(reverse('logs:url_log_summary'))
        self.assertEqual(response.status_code, 200)

        url_data = {item['url']: item['count'] for item in response.context['url_data']}

        self.assertIn('/staff/staff/detail/#/', url_data)
        self.assertEqual(url_data['/staff/staff/detail/#/'], 2, "Staff detail URLs should be aggregated")

        self.assertIn('/staff/', url_data)
        self.assertEqual(url_data['/staff/'], 1, "Staff list URL count should be 1")

        self.assertIn('/', url_data)
        self.assertEqual(url_data['/'], 1, "Home page URL count should be 1")

        self.assertIn('/logs/url/', url_data)
        self.assertEqual(url_data['/logs/url/'], 0, "Log page itself should have a count of 0 in the response")

    def test_sorting(self):
        """
        Test the sorting functionality of the access log view.
        """
        AccessLog.objects.create(url='/', user=self.user)
        AccessLog.objects.create(url='/staff/', user=self.user)
        AccessLog.objects.create(url='/staff/', user=self.user)

        response = self.client.get(reverse('logs:url_log_summary') + '?sort=-count')
        self.assertEqual(response.status_code, 200)
        url_data = response.context['url_data']
        counts = [item['count'] for item in url_data]
        self.assertEqual(counts, sorted(counts, reverse=True), "Should be sorted by count descending")

        response = self.client.get(reverse('logs:url_log_summary') + '?sort=url')
        self.assertEqual(response.status_code, 200)
        url_data = response.context['url_data']
        urls = [item['url'] for item in url_data]
        self.assertEqual(urls, sorted(urls), "Should be sorted by URL ascending")
