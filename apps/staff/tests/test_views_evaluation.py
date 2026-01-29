# apps/staff/tests/test_views_evaluation.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from django.http import JsonResponse

User = get_user_model()

class StaffEvaluationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password', tenant_id=1)
        # Add permission to view staff evaluation
        from django.contrib.auth.models import Permission
        permission = Permission.objects.get(codename='view_staffevaluation')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        self.staff = Staff.objects.create(
            name_last='Test',
            name_first='Staff',
            hire_date='2023-01-01',
            created_by=self.user,
            tenant_id=1
        )

    def test_staff_evaluation_list_ajax_post(self):
        """
        Test that the staff_evaluation_list view returns a JsonResponse
        for an AJAX POST request.
        """
        url = reverse('staff:staff_evaluation_list', kwargs={'staff_pk': self.staff.pk})
        response = self.client.post(
            url,
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)

        # Check if the response contains the expected keys
        data = response.json()
        self.assertIn('ai_response', data)
        self.assertIn('error_message', data)
