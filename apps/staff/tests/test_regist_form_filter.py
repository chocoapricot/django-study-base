from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff
from apps.system.settings.models import Dropdowns
from datetime import date

User = get_user_model()

class RegistFormFilterTest(TestCase):
    """登録区分フィルター機能のテストクラス"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # 権限の設定
        content_type = ContentType.objects.get_for_model(Staff)
        view_permission = Permission.objects.get(codename='view_staff', content_type=content_type)
        self.user.user_permissions.add(view_permission)

        # 登録区分のドロップダウンデータを作成
        Dropdowns.objects.create(category='regist_form', value='1', name='正社員', active=True, disp_seq=1)
        Dropdowns.objects.create(category='regist_form', value='2', name='契約社員', active=True, disp_seq=2)
        Dropdowns.objects.create(category='regist_form', value='10', name='派遣社員', active=True, disp_seq=3)
        Dropdowns.objects.create(category='regist_form', value='20', name='アルバイト', active=True, disp_seq=4)
        Dropdowns.objects.create(category='regist_form', value='90', name='退職者', active=True, disp_seq=5)

        # テスト用スタッフデータを作成
        self.staff_seishain = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
            regist_form_code=1,  # 正社員
            employee_no='EMP001',
            hire_date=date(2020, 4, 1)  # 入社日を追加
        )
        
        self.staff_keiyaku = Staff.objects.create(
            name_last='佐藤',
            name_first='花子',
            name_kana_last='サトウ',
            name_kana_first='ハナコ',
            birth_date=date(1985, 5, 15),
            sex=2,
            regist_form_code=2,  # 契約社員
            employee_no='EMP002',
            hire_date=date(2021, 4, 1)  # 入社日を追加
        )
        
        self.staff_haken = Staff.objects.create(
            name_last='鈴木',
            name_first='次郎',
            name_kana_last='スズキ',
            name_kana_first='ジロウ',
            birth_date=date(1992, 8, 20),
            sex=1,
            regist_form_code=10,  # 派遣社員
            employee_no='EMP003',
            hire_date=date(2022, 4, 1)  # 入社日を追加
        )
        
        self.staff_baito = Staff.objects.create(
            name_last='高橋',
            name_first='三郎',
            name_kana_last='タカハシ',
            name_kana_first='サブロウ',
            birth_date=date(1995, 3, 10),
            sex=1,
            regist_form_code=20,  # アルバイト
            employee_no='EMP004',
            hire_date=date(2023, 4, 1)  # 入社日を追加
        )
        
        self.staff_taishoku = Staff.objects.create(
            name_last='山田',
            name_first='四郎',
            name_kana_last='ヤマダ',
            name_kana_first='シロウ',
            birth_date=date(1980, 12, 25),
            sex=1,
            regist_form_code=90,  # 退職者
            employee_no='EMP005',
            hire_date=date(2018, 4, 1),  # 入社日を追加
            resignation_date=date(2024, 3, 31)  # 退職日も追加
        )

    def test_regist_form_filter_seishain(self):
        """正社員での絞り込みテスト"""
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': '1'})
        self.assertEqual(response.status_code, 200)
        
        # 正社員のスタッフのみが表示されることを確認
        self.assertContains(response, '田中')  # 正社員
        self.assertNotContains(response, '佐藤')  # 契約社員
        self.assertNotContains(response, '鈴木')  # 派遣社員
        self.assertNotContains(response, '高橋')  # アルバイト
        self.assertNotContains(response, '山田')  # 退職者
        
        # フィルター選択状態の確認
        self.assertContains(response, 'value="1" selected')

    def test_regist_form_filter_keiyaku(self):
        """契約社員での絞り込みテスト"""
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': '2'})
        self.assertEqual(response.status_code, 200)
        
        # 契約社員のスタッフのみが表示されることを確認
        self.assertNotContains(response, '田中')  # 正社員
        self.assertContains(response, '佐藤')  # 契約社員
        self.assertNotContains(response, '鈴木')  # 派遣社員
        self.assertNotContains(response, '高橋')  # アルバイト
        self.assertNotContains(response, '山田')  # 退職者
        
        # フィルター選択状態の確認
        self.assertContains(response, 'value="2" selected')

    def test_regist_form_filter_haken(self):
        """派遣社員での絞り込みテスト"""
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': '10'})
        self.assertEqual(response.status_code, 200)
        
        # 派遣社員のスタッフのみが表示されることを確認
        self.assertNotContains(response, '田中')  # 正社員
        self.assertNotContains(response, '佐藤')  # 契約社員
        self.assertContains(response, '鈴木')  # 派遣社員
        self.assertNotContains(response, '高橋')  # アルバイト
        self.assertNotContains(response, '山田')  # 退職者
        
        # フィルター選択状態の確認
        self.assertContains(response, 'value="10" selected')

    def test_regist_form_filter_baito(self):
        """アルバイトでの絞り込みテスト"""
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': '20'})
        self.assertEqual(response.status_code, 200)
        
        # アルバイトのスタッフのみが表示されることを確認
        self.assertNotContains(response, '田中')  # 正社員
        self.assertNotContains(response, '佐藤')  # 契約社員
        self.assertNotContains(response, '鈴木')  # 派遣社員
        self.assertContains(response, '高橋')  # アルバイト
        self.assertNotContains(response, '山田')  # 退職者
        
        # フィルター選択状態の確認
        self.assertContains(response, 'value="20" selected')

    def test_regist_form_filter_taishoku(self):
        """退職者での絞り込みテスト"""
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': '90'})
        self.assertEqual(response.status_code, 200)
        
        # 退職者のスタッフのみが表示されることを確認
        self.assertNotContains(response, '田中')  # 正社員
        self.assertNotContains(response, '佐藤')  # 契約社員
        self.assertNotContains(response, '鈴木')  # 派遣社員
        self.assertNotContains(response, '高橋')  # アルバイト
        self.assertContains(response, '山田')  # 退職者
        
        # フィルター選択状態の確認
        self.assertContains(response, 'value="90" selected')

    def test_regist_form_filter_all(self):
        """全ての登録区分表示テスト（フィルターなし）"""
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        
        # 全てのスタッフが表示されることを確認
        self.assertContains(response, '田中')  # 正社員
        self.assertContains(response, '佐藤')  # 契約社員
        self.assertContains(response, '鈴木')  # 派遣社員
        self.assertContains(response, '高橋')  # アルバイト
        self.assertContains(response, '山田')  # 退職者
        
        # デフォルト選択状態の確認
        self.assertContains(response, 'value="">登録区分（全て）</option>')

    def test_regist_form_filter_with_search(self):
        """検索キーワードと登録区分フィルターの組み合わせテスト"""
        # 「田中」で検索 + 正社員フィルター
        response = self.client.get(reverse('staff:staff_list'), {
            'q': '田中',
            'regist_form': '1'
        })
        self.assertEqual(response.status_code, 200)
        
        # 田中（正社員）のみが表示されることを確認
        self.assertContains(response, '田中')
        self.assertNotContains(response, '佐藤')
        self.assertNotContains(response, '鈴木')
        self.assertNotContains(response, '高橋')
        self.assertNotContains(response, '山田')
        
        # 「田中」で検索 + 契約社員フィルター（該当なし）
        response = self.client.get(reverse('staff:staff_list'), {
            'q': '田中',
            'regist_form': '2'
        })
        self.assertEqual(response.status_code, 200)
        
        # テーブル内に該当するスタッフがいないことを確認
        table_content = response.content.decode()
        tbody_start = table_content.find('<tbody>')
        tbody_end = table_content.find('</tbody>') + len('</tbody>')
        tbody_content = table_content[tbody_start:tbody_end]
        
        # tbody内に名前が含まれていないことを確認
        self.assertNotIn('田中', tbody_content)
        self.assertNotIn('佐藤', tbody_content)
        self.assertNotIn('鈴木', tbody_content)
        self.assertNotIn('高橋', tbody_content)
        self.assertNotIn('山田', tbody_content)

    def test_regist_form_filter_with_sort(self):
        """ソートと登録区分フィルターの組み合わせテスト"""
        # 正社員フィルター + 社員番号昇順ソート
        response = self.client.get(reverse('staff:staff_list'), {
            'regist_form': '1',
            'sort': 'employee_no'
        })
        self.assertEqual(response.status_code, 200)
        
        # 正社員のスタッフのみが表示され、ソートされていることを確認
        self.assertContains(response, '田中')
        self.assertNotContains(response, '佐藤')
        
        # ソートリンクにフィルターパラメータが含まれていることを確認
        self.assertContains(response, 'regist_form=1')

    def test_regist_form_filter_ui_elements(self):
        """登録区分フィルターのUI要素が正しく表示されることをテスト"""
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        
        # セレクトボックスが存在することを確認
        self.assertContains(response, '<select name="regist_form"')
        self.assertContains(response, 'form-select-sm')
        
        # 選択肢が正しく表示されることを確認
        self.assertContains(response, '登録区分（全て）')
        self.assertContains(response, '正社員')
        self.assertContains(response, '契約社員')
        self.assertContains(response, '派遣社員')
        self.assertContains(response, 'アルバイト')
        self.assertContains(response, '退職者')
        
        # リセットボタンが存在することを確認
        self.assertContains(response, 'onclick="resetForm()"')
        
        # JavaScriptのresetForm関数が存在することを確認
        self.assertContains(response, 'function resetForm()')

    def test_regist_form_filter_pagination_links(self):
        """ページネーションリンクに登録区分フィルターパラメータが含まれることをテスト"""
        # 大量のテストデータを作成してページネーションを発生させる
        for i in range(15):
            Staff.objects.create(
                name_last=f'テスト{i:02d}',
                name_first='スタッフ',
                name_kana_last=f'テスト{i:02d}',
                name_kana_first='スタッフ',
                birth_date=date(1990, 1, 1),
                sex=1,
                regist_form_code=1,  # 正社員
                employee_no=f'TEST{i:03d}',
                hire_date=date(2020, 4, (i % 28) + 1)  # 入社日を追加（月内の日付でループ）
            )
        
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': '1'})
        self.assertEqual(response.status_code, 200)
        
        # ページネーションリンクにregist_formパラメータが含まれていることを確認
        self.assertContains(response, 'regist_form=1')
        
        # 次のページリンクを確認
        if response.context['staffs'].has_next:
            self.assertContains(response, f'page={response.context["staffs"].paginator.num_pages}&sort=&q=&regist_form=1')

    def test_regist_form_badge_display(self):
        """登録区分バッジの表示テスト"""
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        
        # 各登録区分に応じたバッジクラスが表示されることを確認
        # 正社員（1）: bg-primary
        self.assertContains(response, 'badge bg-primary')
        
        # 契約社員（2）: bg-primary
        self.assertContains(response, 'badge bg-primary')
        
        # 派遣社員（10）: bg-success
        self.assertContains(response, 'badge bg-success')
        
        # アルバイト（20）: bg-info
        self.assertContains(response, 'badge bg-info')
        
        # 退職者（90）: bg-dark
        self.assertContains(response, 'badge bg-dark')

    def test_invalid_regist_form_filter(self):
        """無効な登録区分フィルター値のテスト"""
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': '999'})
        self.assertEqual(response.status_code, 200)
        
        # 無効な値の場合、結果が0件になることを確認
        table_content = response.content.decode()
        tbody_start = table_content.find('<tbody>')
        tbody_end = table_content.find('</tbody>') + len('</tbody>')
        tbody_content = table_content[tbody_start:tbody_end]
        
        # tbody内にスタッフ名が含まれていないことを確認
        self.assertNotIn('田中', tbody_content)
        self.assertNotIn('佐藤', tbody_content)
        self.assertNotIn('鈴木', tbody_content)
        self.assertNotIn('高橋', tbody_content)
        self.assertNotIn('山田', tbody_content)

    def test_empty_regist_form_filter(self):
        """空の登録区分フィルター値のテスト"""
        response = self.client.get(reverse('staff:staff_list'), {'regist_form': ''})
        self.assertEqual(response.status_code, 200)
        
        # 空の値の場合、全てのスタッフが表示されることを確認
        self.assertContains(response, '田中')
        self.assertContains(response, '佐藤')
        self.assertContains(response, '鈴木')
        self.assertContains(response, '高橋')
        self.assertContains(response, '山田')