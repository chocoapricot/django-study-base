from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import Information
from apps.company.models import Company
from apps.connect.models import ConnectStaff
import datetime

User = get_user_model()

class InformationViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='password')
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        
        # Create more than 10 informations to test pagination
        for i in range(15):
            Information.objects.create(
                subject=f'Test Info {i}',
                content=f'Content for info {i}',
                target='staff',
                corporation_number=self.company.corporate_number,
                start_date=datetime.date.today() - datetime.timedelta(days=1)
            )
            
        ConnectStaff.objects.create(
            email=self.user.email,
            corporate_number=self.company.corporate_number,
            status='approved'
        )

    def test_information_list_view(self):
        """
        information_listビューが正しく動作するかテスト
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(reverse('home:information_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/information_list.html')
        
        # Check pagination
        self.assertTrue('page_obj' in response.context)
        self.assertEqual(len(response.context['page_obj']), 10) # 10 items on the first page
        
        # Check that the last item is on the second page
        response = self.client.get(reverse('home:information_list') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj']), 5) # 5 items on the second page

    def test_information_detail_back_button_from_list(self):
        """
        お知らせ一覧から詳細ページに遷移した際の戻るボタンのテスト
        """
        self.client.login(email='testuser@example.com', password='password')
        list_url = reverse('home:information_list')
        info = Information.objects.first()
        detail_url = reverse('home:information_detail', kwargs={'pk': info.pk})
        
        response = self.client.get(f"{detail_url}?next={list_url}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{list_url}"')

    def test_information_detail_back_button_from_home(self):
        """
        ホームから詳細ページに遷移した際の戻るボタンのテスト
        """
        self.client.login(email='testuser@example.com', password='password')
        home_url = reverse('home:home')
        info = Information.objects.first()
        detail_url = reverse('home:information_detail', kwargs={'pk': info.pk})
        
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{home_url}"')
