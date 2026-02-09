from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from apps.staff.models import Staff
from apps.kintai.models import StaffTimerecord, StaffTimerecordBreak
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from datetime import date, datetime
from unittest.mock import patch

User = get_user_model()

class ReverseGeocodeAPITests(TestCase):
    def setUp(self):
        # テナントを作成
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)

        # ユーザーとスタッフを作成
        self.user = User.objects.create_user(username='staff_user', email='staff@example.com', password='password', tenant_id=self.company.tenant_id)

        # 権限を付与
        permission = Permission.objects.get(codename='view_stafftimerecord')
        self.user.user_permissions.add(permission)

        self.staff = Staff.objects.create(
            employee_no='1001',
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com'
        )
        self.client.login(username='staff_user', password='password')

        # 打刻データを作成（座標あり、住所なし）
        self.timerecord = StaffTimerecord.objects.create(
            staff=self.staff,
            work_date=date(2025, 4, 1),
            start_time=timezone.make_aware(datetime(2025, 4, 1, 9, 0)),
            start_latitude=35.68123,
            start_longitude=139.76709
        )

    @patch('apps.kintai.views_timerecord.fetch_gsi_address')
    def test_reverse_geocode_timerecord_start(self, mock_fetch):
        mock_fetch.return_value = "東京都千代田区丸の内一丁目"

        response = self.client.post(reverse('kintai:timerecord_reverse_geocode'), {
            'model_name': 'timerecord',
            'object_id': self.timerecord.pk,
            'type': 'start'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['address'], "東京都千代田区丸の内一丁目")

        # DBに保存されているか確認
        self.timerecord.refresh_from_db()
        self.assertEqual(self.timerecord.start_address, "東京都千代田区丸の内一丁目")

    @patch('apps.kintai.views_timerecord.fetch_gsi_address')
    def test_reverse_geocode_break_start(self, mock_fetch):
        mock_fetch.return_value = "東京都渋谷区代々木"

        # 休憩データを作成
        break_record = StaffTimerecordBreak.objects.create(
            timerecord=self.timerecord,
            break_start=timezone.make_aware(datetime(2025, 4, 1, 12, 0)),
            start_latitude=35.68306,
            start_longitude=139.70204
        )

        response = self.client.post(reverse('kintai:timerecord_reverse_geocode'), {
            'model_name': 'break',
            'object_id': break_record.pk,
            'type': 'start'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['address'], "東京都渋谷区代々木")

        break_record.refresh_from_db()
        self.assertEqual(break_record.start_address, "東京都渋谷区代々木")

    def test_reverse_geocode_permission_denied(self):
        # 別のスタッフのデータを作成
        other_staff = Staff.objects.create(employee_no='1002', name_last='他', name_first='人', email='other@example.com')
        other_record = StaffTimerecord.objects.create(
            staff=other_staff,
            work_date=date(2025, 4, 1),
            start_time=timezone.make_aware(datetime(2025, 4, 1, 9, 0)),
            start_latitude=35.0,
            start_longitude=135.0
        )

        response = self.client.post(reverse('kintai:timerecord_reverse_geocode'), {
            'model_name': 'timerecord',
            'object_id': other_record.pk,
            'type': 'start'
        })

        # スタッフは自分のデータ以外にはアクセスできない
        self.assertEqual(response.status_code, 403)
