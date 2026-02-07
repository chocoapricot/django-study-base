from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from datetime import date, timedelta
from apps.staff.models import Staff, StaffGrade
from apps.master.models_staff import Grade
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from django_currentuser.middleware import _set_current_user as set_current_user

class StaffGradeBulkChangeTest(TestCase):
    def setUp(self):
        # 会社データの作成
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        set_current_tenant_id(self.company.tenant_id)

        # ユーザーの作成
        User = get_user_model()
        self.user = User.objects.create_user(username='admin', password='password', is_staff=True)
        # 必要な権限を付与
        permissions = Permission.objects.filter(codename__in=['view_staff', 'add_staffgrade', 'view_staffgrade', 'view_grade'])
        self.user.user_permissions.add(*permissions)
        set_current_user(self.user)

        # 等級マスタの作成
        self.grade_a = Grade.objects.create(code='A', name='Grade A', salary_type='hourly', amount=1000, tenant_id=self.company.tenant_id)
        self.grade_b = Grade.objects.create(code='B', name='Grade B', salary_type='hourly', amount=1200, tenant_id=self.company.tenant_id)

        # スタッフデータの作成
        self.staff1 = Staff.objects.create(name_last='山田', name_first='太郎', employee_no='S001', tenant_id=self.company.tenant_id)
        self.staff2 = Staff.objects.create(name_last='佐藤', name_first='花子', employee_no='S002', tenant_id=self.company.tenant_id)

        # 初期の等級設定
        self.sg1 = StaffGrade.objects.create(staff=self.staff1, grade_code='A', valid_from=date(2023, 1, 1), tenant_id=self.company.tenant_id)
        # staff2 は最初等級なしにしようと思ったが、要件は「スタッフ等級が設定されているスタッフ」なので、何か設定する
        self.sg2 = StaffGrade.objects.create(staff=self.staff2, grade_code='A', valid_from=date(2023, 1, 1), tenant_id=self.company.tenant_id)

        self.client = Client()
        self.client.login(username='admin', password='password')

    def test_bulk_change_view_get(self):
        """一括変更画面の表示テスト"""
        response = self.client.get(reverse('staff:staff_grade_bulk_change'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '山田 太郎')
        self.assertContains(response, '佐藤 花子')
        self.assertContains(response, 'Grade A (A)')

    def test_bulk_change_apply(self):
        """一括変更の実行テスト"""
        revision_date = date(2023, 10, 1)
        data = {
            'revision_date': revision_date.strftime('%Y-%m-%d'),
            f'grade_{self.staff1.pk}': 'B',  # A -> B に変更
            f'grade_{self.staff2.pk}': 'A',  # A -> A (変更なし)
        }
        response = self.client.post(reverse('staff:staff_grade_bulk_change'), data)
        self.assertEqual(response.status_code, 302)

        # 結果の確認
        # staff1: 新しい等級が作成されているはず
        self.assertEqual(self.staff1.grades.count(), 2)
        new_grade = self.staff1.grades.get(grade_code='B')
        self.assertEqual(new_grade.valid_from, revision_date)

        # 前の等級が終了しているはず
        old_grade = self.staff1.grades.get(grade_code='A')
        self.assertEqual(old_grade.valid_to, date(2023, 9, 30))

        # staff2: 変更なしのはず
        self.assertEqual(self.staff2.grades.count(), 1)
        self.assertEqual(self.staff2.grades.first().grade_code, 'A')
        self.assertIsNone(self.staff2.grades.first().valid_to)

    def test_bulk_change_overwrite(self):
        """同一開始日のデータがある場合の上書きテスト"""
        revision_date = date(2023, 1, 1) # 初期の開始日と同じ
        data = {
            'revision_date': revision_date.strftime('%Y-%m-%d'),
            f'grade_{self.staff1.pk}': 'B',
        }
        response = self.client.post(reverse('staff:staff_grade_bulk_change'), data)

        # staff1: 既存の 2023-01-01 開始のデータが消えて、新しい B が 2023-01-01 開始で作成されるはず
        self.assertEqual(self.staff1.grades.count(), 1)
        current_grade = self.staff1.grades.first()
        self.assertEqual(current_grade.grade_code, 'B')
        self.assertEqual(current_grade.valid_from, date(2023, 1, 1))
