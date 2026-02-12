from django.test import TestCase
from django.template import Context, Template
from apps.staff.models import Staff, StaffGrade
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

class StaffGradeBulkDurationTest(TestCase):
    def setUp(self):
        # 会社データの作成
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        set_current_tenant_id(self.company.tenant_id)

        # ユーザーの作成
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser_bulk', password='password')
        from django_currentuser.middleware import _set_current_user as set_current_user
        set_current_user(self.user)

        # スタッフデータの作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            tenant_id=self.company.tenant_id
        )

    def test_get_duration_with_reference_date(self):
        """get_duration(reference_date) のテスト"""
        # 2024/01/01 開始の等級
        grade = StaffGrade.objects.create(
            staff=self.staff,
            grade_code='G1',
            valid_from=date(2024, 1, 1),
            tenant_id=self.company.tenant_id
        )

        # 基準日が 2024/04/01 の場合 (Jan, Feb, Mar の3ヶ月)
        # 注意: get_duration(ref) は ref を inclusive とするので、
        # 3ヶ月ちょうどにしたい場合は ref=2024/03/31 にする必要がある
        self.assertEqual(grade.get_duration(date(2024, 3, 31)), "3ヶ月")

        # 2024/01/01 から 2024/04/01 (inclusive) は 3ヶ月と1日 -> "3ヶ月" (日数は表示されない)
        self.assertEqual(grade.get_duration(date(2024, 4, 1)), "3ヶ月")

        # 1年後
        self.assertEqual(grade.get_duration(date(2024, 12, 31)), "1年0ヶ月")

    def test_duration_until_filter(self):
        """duration_until フィルタのテスト"""
        grade = StaffGrade.objects.create(
            staff=self.staff,
            grade_code='G1',
            valid_from=date(2024, 1, 1),
            tenant_id=self.company.tenant_id
        )

        template = Template('{% load staff_tags %}{{ grade|duration_until:revision_date }}')

        # 改定日が 2024/04/01 の場合、3月31日までの期間 = 3ヶ月
        context = Context({'grade': grade, 'revision_date': date(2024, 4, 1)})
        self.assertEqual(template.render(context), "3ヶ月")

        # 改定日が 2025/01/01 の場合、12月31日までの期間 = 1年0ヶ月
        context = Context({'grade': grade, 'revision_date': date(2025, 1, 1)})
        self.assertEqual(template.render(context), "1年0ヶ月")

    def test_current_grade_as_of_filter(self):
        """current_grade_as_of フィルタのテスト"""
        g1 = StaffGrade.objects.create(
            staff=self.staff,
            grade_code='G1',
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 3, 31),
            tenant_id=self.company.tenant_id
        )
        g2 = StaffGrade.objects.create(
            staff=self.staff,
            grade_code='G2',
            valid_from=date(2024, 4, 1),
            tenant_id=self.company.tenant_id
        )

        template = Template('{% load staff_tags %}{{ staff|current_grade_as_of:date }}')

        # 2024/03/01 時点 -> G1
        context = Context({'staff': self.staff, 'date': date(2024, 3, 1)})
        self.assertIn('G1', template.render(context))

        # 2024/04/01 時点 -> G2
        context = Context({'staff': self.staff, 'date': date(2024, 4, 1)})
        self.assertIn('G2', template.render(context))
