from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffContacted
from apps.system.settings.models import Dropdowns
from datetime import date

User = get_user_model()

class StaffSortingTest(TestCase):
    def setUp(self):
        Staff.objects.all().delete() # 既存のStaffオブジェクトをすべて削除
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # StaffモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Staff)
        # 必要な権限をユーザーに付与
        self.view_staff_permission = Permission.objects.get(codename='view_staff', content_type=content_type)
        self.user.user_permissions.add(self.view_staff_permission)

        # Create necessary Dropdowns for StaffForm
        Dropdowns.objects.create(category='sex', value='1', name='男性', active=True, disp_seq=1)
        Dropdowns.objects.create(category='sex', value='2', name='女性', active=True, disp_seq=2)
        Dropdowns.objects.create(category='staff_regist_status', value='1', name='正社員', active=True, disp_seq=1)
        Dropdowns.objects.create(category='staff_regist_status', value='2', name='契約社員', active=True, disp_seq=2)
        # Create necessary Dropdowns for StaffContactedForm
        Dropdowns.objects.create(category='contact_type', value='1', name='電話', active=True, disp_seq=1)
        Dropdowns.objects.create(category='contact_type', value='2', name='メール', active=True, disp_seq=2)

        self.staff_obj = Staff.objects.create(
            name_last='テスト',
            name_first='スタッフ',
            name_kana_last='テスト',
            name_kana_first='スタッフ',
            birth_date=date(2015, 7, 30), # ageを10にするためにbirth_dateを設定
            sex=1,
            staff_regist_status_code=1,
            employee_no='ZEMP000', # ソート順で最後にくるように変更
            hire_date=date(2019, 4, 1),  # 入社日を追加
            email='test@example.com',
            address1='テスト住所' # address1を追加
        )
        # ソートテスト用のスタッフデータを作成 (12件)
        for i in range(1, 13):
            Staff.objects.create(
                name_last=f'Staff {i:02d}',
                name_first='Test',
                name_kana_last=f'スタッフ{i:02d}',
                name_kana_first='テスト',
                birth_date=date(2005 - i, 7, 30), # ageを20+iにするためにbirth_dateを設定
                sex=1,
                staff_regist_status_code=1,
                employee_no=f'EMP{i:03d}',
                hire_date=date(2020, 4, i),  # 入社日を追加（日付を変える）
                email=f'staff{i:02d}@example.com',
                address1=f'住所{i:02d}'
            )

    def test_staff_list_sort_pagination(self):
        """スタッフ一覧でソート条件がページ移動後も保持されることをテスト"""
        # 1. 社員番号で昇順ソートして1ページ目にアクセス
        response = self.client.get(reverse('staff:staff_list'), {'sort': 'employee_no', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].employee_no, 'EMP001')
        self.assertEqual(staffs_on_page[9].employee_no, 'EMP010')

        # 2. 2ページ目に移動
        response = self.client.get(reverse('staff:staff_list'), {'sort': 'employee_no', 'page': 2})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].employee_no, 'EMP011')
        self.assertEqual(staffs_on_page[1].employee_no, 'EMP012')
        self.assertEqual(staffs_on_page[2].employee_no, 'ZEMP000') # self.staff_obj

        # 3. 氏名（姓）で降順ソートして1ページ目にアクセス
        response = self.client.get(reverse('staff:staff_list'), {'sort': '-name_last', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].name_last, 'テスト') # self.staff_obj
        self.assertEqual(staffs_on_page[1].name_last, 'Staff 12')
        self.assertEqual(staffs_on_page[9].name_last, 'Staff 04')

        # 4. 降順ソートを保持したまま2ページ目に移動
        response = self.client.get(reverse('staff:staff_list'), {'sort': '-name_last', 'page': 2})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].name_last, 'Staff 03')
        self.assertEqual(staffs_on_page[1].name_last, 'Staff 02')
        self.assertEqual(staffs_on_page[2].name_last, 'Staff 01')

        # 5. 検索クエリとソート条件を組み合わせてテスト (例: 'Staff 0'で検索し、社員番号昇順ソート)
        response = self.client.get(reverse('staff:staff_list'), {'sort': 'employee_no', 'q': 'Staff 0', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].employee_no, 'EMP001')
        self.assertEqual(staffs_on_page[1].employee_no, 'EMP002')
        self.assertEqual(len(staffs_on_page), 9) # Staff 01-09の9件

        # 6. 検索クエリとソート条件を組み合わせてテスト (例: 'Staff 1'で検索し、社員番号昇順ソート)
        response = self.client.get(reverse('staff:staff_list'), {'sort': 'employee_no', 'q': 'Staff 1', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].employee_no, 'EMP010')
        self.assertEqual(staffs_on_page[1].employee_no, 'EMP011')
        self.assertEqual(staffs_on_page[2].employee_no, 'EMP012')
        self.assertEqual(len(staffs_on_page), 3) # Staff 10-12の3件

        # 7. 住所で昇順ソートして1ページ目にアクセス
        response = self.client.get(reverse('staff:staff_list'), {'sort': 'address1', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].address1, 'テスト住所') # self.staff_obj
        self.assertEqual(staffs_on_page[1].address1, '住所01')
        self.assertEqual(staffs_on_page[9].address1, '住所09') # 10番目の要素は住所09

        # 8. 住所で降順ソートして1ページ目にアクセス
        response = self.client.get(reverse('staff:staff_list'), {'sort': '-address1', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        self.assertEqual(staffs_on_page[0].address1, '住所12')
        self.assertEqual(staffs_on_page[9].address1, '住所03')

        # 9. 年齢で昇順ソートして1ページ目にアクセス
        response = self.client.get(reverse('staff:staff_list'), {'sort': 'age', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        print(f"Ages on page (ascending): {[s.age for s in staffs_on_page]}")
        self.assertEqual(staffs_on_page[0].age, 10) # self.staff_obj
        self.assertEqual(staffs_on_page[9].age, 29) # 20 + 9

        # 10. 年齢で降順ソートして1ページ目にアクセス
        response = self.client.get(reverse('staff:staff_list'), {'sort': '-age', 'page': 1})
        self.assertEqual(response.status_code, 200)
        staffs_on_page = response.context['staffs'].object_list
        print(f"Ages on page (descending): {[s.age for s in staffs_on_page]}")
        self.assertEqual(staffs_on_page[0].age, 32) # 20 + 12
        self.assertEqual(staffs_on_page[9].age, 23) # 20 + 3