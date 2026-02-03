from django.test import TestCase, RequestFactory
from django.template import Context, Template
from django.contrib.auth import get_user_model
from apps.staff.models import Staff, StaffFavorite
from apps.client.models import Client, ClientFavorite

User = get_user_model()

class FavoriteTagsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password', first_name='Test', last_name='User')
        self.staff = Staff.objects.create(
            name_last='Test', name_first='Staff',
            tenant_id=1
        )
        self.client = Client.objects.create(
            name='Test Client',
            tenant_id=1
        )

    def test_staff_favorite_star_tag(self):
        # Staff favorite not set
        request = self.factory.get('/')
        request.user = self.user

        template = Template('{% load favorite_tags %}{% favorite_star staff %}')
        context = Context({'request': request, 'staff': self.staff})
        rendered = template.render(context)
        self.assertEqual(rendered, '')

        # Set staff favorite
        StaffFavorite.objects.create(staff=self.staff, user=self.user, tenant_id=1)

        # New request to clear cache if it was stored on request object
        request = self.factory.get('/')
        request.user = self.user
        context = Context({'request': request, 'staff': self.staff})
        rendered = template.render(context)
        self.assertIn('bi-star-fill', rendered)
        self.assertIn('text-warning', rendered)

    def test_client_favorite_star_tag(self):
        # Client favorite not set
        request = self.factory.get('/')
        request.user = self.user

        template = Template('{% load favorite_tags %}{% favorite_star client %}')
        context = Context({'request': request, 'client': self.client})
        rendered = template.render(context)
        self.assertEqual(rendered, '')

        # Set client favorite
        ClientFavorite.objects.create(client=self.client, user=self.user, tenant_id=1)

        request = self.factory.get('/')
        request.user = self.user
        context = Context({'request': request, 'client': self.client})
        rendered = template.render(context)
        self.assertIn('bi-star-fill', rendered)
        self.assertIn('text-warning', rendered)

    def test_favorite_star_hide_favorite(self):
        StaffFavorite.objects.create(staff=self.staff, user=self.user, tenant_id=1)
        request = self.factory.get('/')
        request.user = self.user

        template = Template('{% load favorite_tags %}{% favorite_star staff %}')
        context = Context({'request': request, 'staff': self.staff, 'hide_favorite': True})
        rendered = template.render(context)
        self.assertEqual(rendered, '')
