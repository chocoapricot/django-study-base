from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffContacted, StaffBank, StaffInternational
from apps.system.settings.models import Dropdowns, Parameter
from apps.master.models import StaffRegistStatus
from datetime import date, datetime 
from django.utils import timezone
from apps.connect.models import ConnectStaff, ProfileRequest
from apps.profile.models import StaffProfile
from urllib.parse import quote

User = get_user_model()

class StaffViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # StaffモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Staff)
        # 必要な権限をユーザーに付与
        self.view_staff_permission = Permission.objects.get(codename='view_staff', content_type=content_type)
        self.add_staff_permission = Permission.objects.get(codename='add_staff', content_type=content_type)
        self.change_staff_permission = Permission.objects.get(codename='change_staff', content_type=content_type)
        self.delete_staff_permission = Permission.objects.get(codename='delete_staff', content_type=content_type)

        self.user.user_permissions.add(self.view_staff_permission)
        self.user.user_permissions.add(self.add_staff_permission)
        self.user.user_permissions.add(self.change_staff_permission)
        self.user.user_permissions.add(self.delete_staff_permission)

        # StaffContactedモデルのContentTypeを取得
        contacted_content_type = ContentType.objects.get_for_model(StaffContacted)
        self.view_staffcontacted_permission = Permission.objects.get(codename='view_staffcontacted', content_type=contacted_content_type)
        self.add_staffcontacted_permission = Permission.objects.get(codename='add_staffcontacted', content_type=contacted_content_type)
        self.change_staffcontacted_permission = Permission.objects.get(codename='change_staffcontacted', content_type=contacted_content_type)
        self.delete_staffcontacted_permission = Permission.objects.get(codename='delete_staffcontacted', content_type=contacted_content_type)

        self.user.user_permissions.add(self.view_staffcontacted_permission)
        self.user.user_permissions.add(self.add_staffcontacted_permission)
        self.user.user_permissions.add(self.change_staffcontacted_permission)
        self.user.user_permissions.add(self.delete_staffcontacted_permission)

        # StaffBankモデルのContentTypeを取得
        bank_content_type = ContentType.objects.get_for_model(StaffBank)
        self.view_staffbank_permission = Permission.objects.get(codename='view_staffbank', content_type=bank_content_type)
        self.add_staffbank_permission = Permission.objects.get(codename='add_staffbank', content_type=bank_content_type)
        self.change_staffbank_permission = Permission.objects.get(codename='change_staffbank', content_type=bank_content_type)
        self.delete_staffbank_permission = Permission.objects.get(codename='delete_staffbank', content_type=bank_content_type)

        self.user.user_permissions.add(self.view_staffbank_permission)
        self.user.user_permissions.add(self.add_staffbank_permission)
        self.user.user_permissions.add(self.change_staffbank_permission)
        self.user.user_permissions.add(self.delete_staffbank_permission)

        # StaffInternationalモデルのContentTypeを取得
        international_content_type = ContentType.objects.get_for_model(StaffInternational)
        self.view_staffinternational_permission = Permission.objects.get(codename='view_staffinternational', content_type=international_content_type)
        self.add_staffinternational_permission = Permission.objects.get(codename='add_staffinternational', content_type=international_content_type)
        self.change_staffinternational_permission = Permission.objects.get(codename='change_staffinternational', content_type=international_content_type)
        self.delete_staffinternational_permission = Permission.objects.get(codename='delete_staffinternational', content_type=international_content_type)

        self.user.user_permissions.add(self.view_staffinternational_permission)
        self.user.user_permissions.add(self.add_staffinternational_permission)
        self.user.user_permissions.add(self.change_staffinternational_permission)
        self.user.user_permissions.add(self.delete_staffinternational_permission)

        # Create necessary Dropdowns for StaffForm
        Dropdowns.objects.create(category='sex', value='1', name='男性', active=True, disp_seq=1)
        Dropdowns.objects.create(category='sex', value='2', name='女性', active=True, disp_seq=2)
        
        # スタッフ登録区分マスタを作成
        self.regist_status_1 = StaffRegistStatus.objects.create(name='正社員', display_order=1, is_active=True)
        self.regist_status_2 = StaffRegistStatus.objects.create(name='契約社員', display_order=2, is_active=True)
        self.regist_status_10 = StaffRegistStatus.objects.create(name='派遣社員', display_order=3, is_active=True)
        
        # 雇用形態マスタを作成
        from apps.master.models import EmploymentType
        EmploymentType.objects.create(name='正社員', display_order=1, is_fixed_term=False, is_active=True)
        EmploymentType.objects.create(name='契約社員', display_order=2, is_fixed_term=True, is_active=True)
        # Create necessary Dropdowns for StaffContactedForm
        Dropdowns.objects.create(category='contact_type', value='1', name='電話', active=True, disp_seq=1)
        Dropdowns.objects.create(category='contact_type', value='2', name='メール', active=True, disp_seq=2)

        # テスト用スタッフデータを作成
        self.staff1 = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
            regist_status=self.regist_status_1,  # 正社員
            employee_no='EMP001',
            hire_date=date(2020, 4, 1)  # 入社日を追加
        )
        
        self.staff2 = Staff.objects.create(
            name_last='佐藤',
            name_first='花子',
            name_kana_last='サトウ',
            name_kana_first='ハナコ',
            birth_date=date(1985, 5, 15),
            sex=2,
            regist_status=self.regist_status_2,  # 契約社員
            employee_no='EMP002',
            hire_date=date(2021, 4, 1)  # 入社日を追加
        )
        
        self.staff3 = Staff.objects.create(
            name_last='鈴木',
            name_first='次郎',
            name_kana_last='スズキ',
            name_kana_first='ジロウ',
            birth_date=date(1992, 8, 20),
            sex=1,
            regist_status=self.regist_status_10,  # 派遣社員
            employee_no='EMP003',
            hire_date=date(2022, 4, 1)  # 入社日を追加
        )

        self.staff_obj = Staff.objects.create(
            name_last='テスト',
            name_first='スタッフ',
            name_kana_last='テスト',
            name_kana_first='スタッフ',
            birth_date=date(1990, 1, 1),
            sex=1,
            regist_status=self.regist_status_1,
            employee_no='ZEMP000', # ソート順で最後にくるように変更
            hire_date=date(2019, 4, 1),  # 入社日を追加
            email='test@example.com',
            address1='東京都',
            address2='千代田区',
            address3='1-1-1',
            age=10 # ageを10に変更
        )
        # ソートテスト用のスタッフデータを作成 (12件)
        for i in range(4, 16):
            Staff.objects.create(
                name_last=f'Staff {i:02d}',
                name_first='Test',
                name_kana_last=f'スタッフ{i:02d}',
                name_kana_first='テスト',
                birth_date=date(1990, 1, 1),
                sex=1,
                regist_status=self.regist_status_1,
                employee_no=f'EMP{i:03d}',
                hire_date=date(2020, 4, i),  # 入社日を追加（日付を変える）
                email=f'staff{i:02d}@example.com',
                address1=f'住所{i:02d}',
                age=20 + i
            )

    def test_staff_list_view(self):
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_list.html')
        self.assertContains(response, 'テスト')

    def test_staff_list_staff_regist_status_filter(self):
        """登録区分での絞り込み機能をテスト"""
        # 1. 正社員のみを絞り込み
        response = self.client.get(reverse('staff:staff_list'), {'regist_status': self.regist_status_1.pk})
        self.assertEqual(response.status_code, 200)
        
        # 正社員のスタッフが表示されることを確認
        self.assertContains(response, '田中')  # staff1 (正社員)
        self.assertNotContains(response, '佐藤')  # staff2 (契約社員)
        self.assertNotContains(response, '鈴木')  # staff3 (派遣社員)
        
        # 2. 契約社員のみを絞り込み
        response = self.client.get(reverse('staff:staff_list'), {'regist_status': self.regist_status_2.pk})
        self.assertEqual(response.status_code, 200)
        
        # 契約社員のスタッフが表示されることを確認
        self.assertNotContains(response, '田中')  # staff1 (正社員)
        self.assertContains(response, '佐藤')  # staff2 (契約社員)
        self.assertNotContains(response, '鈴木')  # staff3 (派遣社員)
        
        # 3. 派遣社員のみを絞り込み
        response = self.client.get(reverse('staff:staff_list'), {'regist_status': self.regist_status_10.pk})
        self.assertEqual(response.status_code, 200)
        
        # 派遣社員のスタッフが表示されることを確認
        self.assertNotContains(response, '田中')  # staff1 (正社員)
        self.assertNotContains(response, '佐藤')  # staff2 (契約社員)
        self.assertContains(response, '鈴木')  # staff3 (派遣社員)
        
        # 4. フィルターなし（全て表示）
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        
        # 全てのスタッフが表示されることを確認
        self.assertContains(response, '田中')  # staff1
        self.assertContains(response, '佐藤')  # staff2
        self.assertContains(response, '鈴木')  # staff3

    def test_staff_list_combined_search_and_filter(self):
        """検索キーワードと登録区分フィルターの組み合わせテスト"""
        # 1. 「田中」で検索 + 正社員フィルター
        response = self.client.get(reverse('staff:staff_list'), {
            'q': '田中',
            'regist_status': self.regist_status_1.pk
        })
        self.assertEqual(response.status_code, 200)
        
        # 田中（正社員）のみが表示されることを確認
        self.assertContains(response, '田中')
        self.assertNotContains(response, '佐藤')
        self.assertNotContains(response, '鈴木')
        
        # 2. 「田中」で検索 + 契約社員フィルター（該当なし）
        response = self.client.get(reverse('staff:staff_list'), {
            'q': '田中',
            'regist_status': self.regist_status_2.pk
        })
        self.assertEqual(response.status_code, 200)
        
        # テーブル内に該当するスタッフがいないことを確認（検索フォームの値は除外）
        # テーブルのtbody部分のみをチェック
        self.assertContains(response, '<tbody>')
        self.assertContains(response, '</tbody>')
        # テーブル内に名前が表示されていないことを確認
        table_content = response.content.decode()
        tbody_start = table_content.find('<tbody>')
        tbody_end = table_content.find('</tbody>') + len('</tbody>')
        tbody_content = table_content[tbody_start:tbody_end]
        
        # tbody内に名前が含まれていないことを確認
        self.assertNotIn('田中', tbody_content)
        self.assertNotIn('佐藤', tbody_content)
        self.assertNotIn('鈴木', tbody_content)

    def test_staff_list_staff_regist_status_options(self):
        """登録区分の選択肢が正しく表示されることをテスト"""
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        
        # 登録区分の選択肢が含まれていることを確認
        self.assertContains(response, '登録区分（全て）')
        self.assertContains(response, '正社員')
        self.assertContains(response, '契約社員')
        self.assertContains(response, '派遣社員')
        
        # selectタグが存在することを確認
        self.assertContains(response, '<select name="regist_status"')
        self.assertContains(response, 'スタッフ')

    def test_staff_regist_status_filter_ui_elements(self):
        """登録区分フィルターのUI要素が正しく表示されることをテスト"""
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        
        # 検索フォームの要素が存在することを確認
        self.assertContains(response, 'input-group-text')
        self.assertNotContains(response, 'input-group-text-sm')
        self.assertContains(response, 'form-control-sm')
        self.assertContains(response, 'form-select-sm')
        
        # 高さ調整のインラインCSSが適用されていないことを確認
        self.assertNotContains(response, 'height: calc(1.5em + 0.5rem + 2px)')
        
        # 検索キーワード入力欄の幅設定を確認
        self.assertContains(response, 'width: 25em')
        
        # 登録区分セレクトボックスの幅設定を確認
        self.assertContains(response, 'width: 12em')

        # selectの親divにinput-groupクラスがあることを確認
        self.assertContains(response, '<div class="input-group me-2 mb-2" style="width: 12em;">')
        
        # 検索・リセットボタンが存在することを確認
        self.assertContains(response, 'type="submit"')
        self.assertContains(response, 'onclick="resetForm()"')

    def test_staff_create_view_get(self):
        response = self.client.get(reverse('staff:staff_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_form.html')

    def test_staff_create_view_post(self):
        data = {
            'name_last': '新規',
            'name_first': 'スタッフ',
            'name_kana_last': 'シンキ',
            'name_kana_first': 'スタッフ',
            'birth_date': '1995-05-05',
            'sex': 2,
            'regist_status': self.regist_status_2.pk,
            'employee_no': 'EMP999',
            'employment_type': 2,  # 雇用形態を追加
            'hire_date': '2024-04-01',  # 社員番号と入社日をセットで設定
            'email': 'newstaff@example.com'
        }
        response = self.client.post(reverse('staff:staff_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_list
        self.assertTrue(Staff.objects.filter(name_last='新規', name_first='スタッフ').exists())

    def test_staff_detail_view(self):
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_detail.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_update_view_get(self):
        response = self.client.get(reverse('staff:staff_update', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_form.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_update_view_post(self):
        data = {
            'name_last': '更新',
            'name_first': 'スタッフ',
            'name_kana_last': 'コウシン',
            'name_kana_first': 'スタッフ',
            'birth_date': '1990-01-01',
            'sex': 1,
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP998',
            'employment_type': 1,  # 雇用形態を追加
            'hire_date': '2020-04-01',  # 社員番号と入社日をセットで設定
            'email': 'test@example.com'
        }
        response = self.client.post(reverse('staff:staff_update', args=[self.staff_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_detail
        self.staff_obj.refresh_from_db()
        self.assertEqual(self.staff_obj.name_last, '更新')

    def test_staff_delete_view_get(self):
        response = self.client.get(reverse('staff:staff_delete', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_confirm_delete.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_delete_view_post(self):
        response = self.client.post(reverse('staff:staff_delete', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to staff_list
        self.assertFalse(Staff.objects.filter(pk=self.staff_obj.pk).exists())

    def test_staff_contacted_create_view_get(self):
        response = self.client.get(reverse('staff:staff_contacted_create', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_form.html')

    def test_staff_contacted_create_view_post(self):
        data = {
            'content': 'テスト連絡',
            'detail': 'これはテスト連絡の詳細です。',
            'contact_type': 1,
            'contacted_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')  # 現在の日時を設定
        }
        response = self.client.post(reverse('staff:staff_contacted_create', args=[self.staff_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_detail
        self.assertTrue(StaffContacted.objects.filter(staff=self.staff_obj, content='テスト連絡').exists())

    def test_staff_contacted_list_view(self):
        StaffContacted.objects.create(staff=self.staff_obj, content='連絡1',contacted_at=timezone.now())
        StaffContacted.objects.create(staff=self.staff_obj, content='連絡2',contacted_at=timezone.now())
        response = self.client.get(reverse('staff:staff_contacted_list', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_list.html')
        self.assertContains(response, '連絡1')
        self.assertContains(response, '連絡2')

    def test_staff_contacted_detail_view(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='詳細テスト連絡', detail='詳細',contacted_at=timezone.now())
        response = self.client.get(reverse('staff:staff_contacted_detail', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_detail.html')
        self.assertContains(response, '詳細')

    def test_staff_contacted_update_view_get(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='元の連絡',contacted_at=timezone.now())
        response = self.client.get(reverse('staff:staff_contacted_update', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_form.html')
        self.assertContains(response, '元の連絡')

    def test_staff_contacted_update_view_post(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='元の連絡',contacted_at=timezone.now())
        data = {
            'content': '更新された連絡',
            'detail': '更新された連絡の詳細です。',
            'contact_type': 2,
            'contacted_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')  # 現在の日時を設定
        }
        response = self.client.post(reverse('staff:staff_contacted_update', args=[contacted_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_detail
        contacted_obj.refresh_from_db()
        self.assertEqual(contacted_obj.content, '更新された連絡')

    def test_staff_contacted_delete_view_get(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='削除テスト連絡',contacted_at=timezone.now())
        response = self.client.get(reverse('staff:staff_contacted_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_confirm_delete.html')
        self.assertContains(response, '削除テスト連絡')

    def test_staff_contacted_delete_view_post(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='削除テスト連絡',contacted_at=timezone.now())
        response = self.client.post(reverse('staff:staff_contacted_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to staff_detail
        self.assertFalse(StaffContacted.objects.filter(pk=contacted_obj.pk).exists())

    def test_staff_change_history_list_view(self):
        response = self.client.get(reverse('staff:staff_change_history_list', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'common/common_change_history_list.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_list_filter_by_request(self):
        """
        Test that the staff list can be filtered by `has_request=true`.
        """
        # Create a staff with a pending request
        staff_user_with_request = User.objects.create_user(
            username='staffwithrequest',
            email='with_request@example.com',
            password='testpassword'
        )
        staff_profile_with_request = StaffProfile.objects.create(
            user=staff_user_with_request,
            name_last='With',
            name_first='Request'
        )
        staff_with_request = Staff.objects.create(email='with_request@example.com', name_last='With', name_first='Request')
        connect_staff_with_request = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email=staff_with_request.email,
            status='approved'
        )
        ProfileRequest.objects.create(
            connect_staff=connect_staff_with_request,
            staff_profile=staff_profile_with_request,
            status='pending'
        )

        # Create a staff without a pending request
        staff_without_request = Staff.objects.create(email='without_request@example.com', name_last='Without', name_first='Request')

        # Test with filter
        response = self.client.get(reverse('staff:staff_list') + '?has_request=true')
        self.assertEqual(response.status_code, 200)

        staff_list_on_page = response.context['staffs'].object_list
        self.assertEqual(len(staff_list_on_page), 1)
        self.assertEqual(staff_list_on_page[0], staff_with_request)

    def test_staff_detail_address_link(self):
        """
        Test the address link in the staff detail view.
        The link should only be displayed if the GOOGLE_MAPS_SEARCH_URL_BASE parameter is set.
        """
        # 1. Parameter is not set
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'bi-box-arrow-up-right')

        # 2. Parameter is set
        Parameter.objects.create(
            key='GOOGLE_MAPS_SEARCH_URL_BASE',
            value='https://maps.google.com/?q=',
            active=True
        )
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bi-box-arrow-up-right')
        self.assertContains(response, f'href="https://maps.google.com/?q={quote(self.staff_obj.full_address)}"')