from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth.models import Permission
from apps.client.models import Client, ClientContacted
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from datetime import date, datetime 
from django.utils import timezone

User = get_user_model()

class ClientViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # ClientモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Client)
        # 必要な権限をユーザーに付与
        self.view_client_permission = Permission.objects.get(codename='view_client', content_type=content_type)
        self.add_client_permission = Permission.objects.get(codename='add_client', content_type=content_type)
        self.change_client_permission = Permission.objects.get(codename='change_client', content_type=content_type)
        self.delete_client_permission = Permission.objects.get(codename='delete_client', content_type=content_type)

        self.user.user_permissions.add(self.view_client_permission)
        self.user.user_permissions.add(self.add_client_permission)
        self.user.user_permissions.add(self.change_client_permission)
        self.user.user_permissions.add(self.delete_client_permission)

        # ClientContactedモデルのContentTypeを取得
        contacted_content_type = ContentType.objects.get_for_model(ClientContacted)
        self.view_clientcontacted_permission = Permission.objects.get(codename='view_clientcontacted', content_type=contacted_content_type)
        self.add_clientcontacted_permission = Permission.objects.get(codename='add_clientcontacted', content_type=contacted_content_type)
        self.change_clientcontacted_permission = Permission.objects.get(codename='change_clientcontacted', content_type=contacted_content_type)
        self.delete_clientcontacted_permission = Permission.objects.get(codename='delete_clientcontacted', content_type=contacted_content_type)

        self.user.user_permissions.add(self.view_clientcontacted_permission)
        self.user.user_permissions.add(self.add_clientcontacted_permission)
        self.user.user_permissions.add(self.change_clientcontacted_permission)
        self.user.user_permissions.add(self.delete_clientcontacted_permission)

        from apps.system.settings.models import Dropdowns
        # Create necessary Dropdowns for ClientForm
        Dropdowns.objects.create(category='regist_form_client', value='1', name='Test Regist Form', active=True, disp_seq=1)
        # Create necessary Dropdowns for ClientContactedForm
        Dropdowns.objects.create(category='contact_type', value='1', name='Test Contact Type 1', active=True, disp_seq=1)
        Dropdowns.objects.create(category='contact_type', value='2', name='Test Contact Type 2', active=True, disp_seq=2)

        # self.client_obj = Client.objects.create(
        #     corporate_number='9999999999999', # より大きな値に設定
        #     name='Test Client',
        #     name_furigana='テストクライアント',
        #     regist_form_client=1
        # )
        # ソートテスト用のクライアントデータを作成 (12件)
        for i in range(1, 13):
            Client.objects.create(
                corporate_number=f'10000000000{i:02d}', # 衝突しないように調整
                name=f'Client {i:02d}',
                name_furigana=f'クライアント{i:02d}',
                regist_form_client=1
            )
        self.client_obj = Client.objects.create(
            corporate_number='9999999999999', # より大きな値に設定
            name='Z_Test Client', # ソート順で最後にくるように変更
            name_furigana='ゼットテストクライアント',
            regist_form_client=1
        )

    def test_client_list_view(self):
        response = self.client.get(reverse('client:client_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_list.html')
        # 1ページ目にはClient 01-10が表示される
        self.assertContains(response, 'Client 01')
        self.assertContains(response, 'Client 10')
        # Z_Test Clientは2ページ目に表示されるため、2ページ目もテスト
        response_page2 = self.client.get(reverse('client:client_list'), {'page': 2})
        self.assertEqual(response_page2.status_code, 200)
        self.assertContains(response_page2, 'Z_Test Client')

    def test_client_list_sort_pagination(self):
        """クライアント一覧でソート条件がページ移動後も保持されることをテスト"""
        # 1. 会社名で昇順ソートして1ページ目にアクセス
        response = self.client.get(reverse('client:client_list'), {'sort': 'name', 'page': 1})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 01')
        self.assertEqual(clients_on_page[9].name, 'Client 10') # 10番目のクライアント

        # 2. 2ページ目に移動
        response = self.client.get(reverse('client:client_list'), {'sort': 'name', 'page': 2})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 11')
        self.assertEqual(clients_on_page[1].name, 'Client 12')
        self.assertEqual(clients_on_page[2].name, 'Z_Test Client') # Z_Test Clientが2ページ目に表示されることを確認

        # 3. 会社名で降順ソートして1ページ目にアクセス
        response = self.client.get(reverse('client:client_list'), {'sort': '-name', 'page': 1})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Z_Test Client') # Z_Test Clientが最初に表示されることを確認
        self.assertEqual(clients_on_page[1].name, 'Client 12')
        self.assertEqual(clients_on_page[9].name, 'Client 04') # 10番目のクライアント

        # 4. 降順ソートを保持したまま2ページ目に移動
        response = self.client.get(reverse('client:client_list'), {'sort': '-name', 'page': 2})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 03')
        self.assertEqual(clients_on_page[1].name, 'Client 02')
        self.assertEqual(clients_on_page[2].name, 'Client 01')

        # 5. 検索クエリとソート条件を組み合わせてテスト (例: 'Client 0'で検索し、名前昇順ソート)
        response = self.client.get(reverse('client:client_list'), {'sort': 'name', 'q': 'Client 0', 'page': 1})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 01')
        self.assertEqual(clients_on_page[1].name, 'Client 02')

    def test_client_list_regist_form_filter(self):
        """クライアント一覧で登録区分による絞り込み機能をテスト"""
        from apps.system.settings.models import Dropdowns
        
        # 追加の登録区分データを作成
        Dropdowns.objects.create(category='regist_form_client', value='10', name='登録済', active=True, disp_seq=2)
        Dropdowns.objects.create(category='regist_form_client', value='20', name='商談中', active=True, disp_seq=3)
        
        # 異なる登録区分のクライアントを作成
        client1 = Client.objects.create(
            corporate_number='1111111111111',
            name='登録中クライアント',
            name_furigana='トウロクチュウクライアント',
            regist_form_client=1
        )
        client2 = Client.objects.create(
            corporate_number='2222222222222',
            name='登録済クライアント',
            name_furigana='トウロクズミクライアント',
            regist_form_client=10
        )
        client3 = Client.objects.create(
            corporate_number='3333333333333',
            name='商談中クライアント',
            name_furigana='ショウダンチュウクライアント',
            regist_form_client=20
        )
        
        # 1. 全件表示（フィルタなし）
        response = self.client.get(reverse('client:client_list'))
        self.assertEqual(response.status_code, 200)
        # 新しく作成したクライアントが表示されることを確認
        # ページネーションがあるので、全ページをチェック
        all_content = response.content.decode()
        if '登録中クライアント' not in all_content:
            # 2ページ目もチェック
            response_page2 = self.client.get(reverse('client:client_list'), {'page': 2})
            all_content += response_page2.content.decode()
        
        self.assertIn('登録中クライアント', all_content)
        self.assertIn('登録済クライアント', all_content)
        self.assertIn('商談中クライアント', all_content)
        
        # 2. 登録区分「1」（登録中）で絞り込み
        response = self.client.get(reverse('client:client_list'), {'regist_form_client': '1'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # ページネーションがある場合は全ページをチェック
        if '登録中クライアント' not in content:
            response_page2 = self.client.get(reverse('client:client_list'), {'regist_form_client': '1', 'page': 2})
            content += response_page2.content.decode()
        
        self.assertIn('登録中クライアント', content)
        self.assertNotIn('登録済クライアント', content)
        self.assertNotIn('商談中クライアント', content)
        
        # 3. 登録区分「10」（登録済）で絞り込み
        response = self.client.get(reverse('client:client_list'), {'regist_form_client': '10'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('登録中クライアント', content)
        self.assertIn('登録済クライアント', content)
        self.assertNotIn('商談中クライアント', content)
        
        # 4. 登録区分「20」（商談中）で絞り込み
        response = self.client.get(reverse('client:client_list'), {'regist_form_client': '20'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('登録中クライアント', content)
        self.assertNotIn('登録済クライアント', content)
        self.assertIn('商談中クライアント', content)
        
        # 5. キーワード検索と登録区分の組み合わせ
        response = self.client.get(reverse('client:client_list'), {
            'q': '登録済',
            'regist_form_client': '10'
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('登録中クライアント', content)
        self.assertIn('登録済クライアント', content)
        self.assertNotIn('商談中クライアント', content)
        
        # 6. ドロップダウンオプションがテンプレートに渡されていることを確認
        response = self.client.get(reverse('client:client_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('regist_form_options', response.context)
        regist_form_options = response.context['regist_form_options']
        self.assertTrue(regist_form_options.count() >= 3)  # 最低3つのオプションがあることを確認

        # 6. 検索クエリとソート条件を組み合わせてテスト (例: 'Client 0'で検索し、名前昇順ソート)
        response = self.client.get(reverse('client:client_list'), {'sort': 'name', 'q': 'Client 0', 'page': 1})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 01')
        self.assertEqual(clients_on_page[1].name, 'Client 02')

        # 6. 検索クエリとソート条件を組み合わせてテスト (例: 'Client 0'で検索し、名前昇順ソート)
        response = self.client.get(reverse('client:client_list'), {'sort': 'name', 'q': 'Client 0', 'page': 1})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 01')
        self.assertEqual(clients_on_page[1].name, 'Client 02')

        # 6. 検索クエリとソート条件を組み合わせてテスト (例: 'Client 0'で検索し、名前昇順ソート)
        response = self.client.get(reverse('client:client_list'), {'sort': 'name', 'q': 'Client 0', 'page': 1})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 01')
        self.assertEqual(clients_on_page[1].name, 'Client 02')

        # 6. 検索クエリとソート条件を保持したまま2ページ目に移動 (Client 01-09)
        # 'Client 0'で検索すると Client 01-09 の9件がヒットする
        # ここでは、検索結果が正しく表示されることを確認する
        self.assertEqual(len(clients_on_page), 9) # 9件のクライアントが検索されることを確認

        # 7. 検索クエリとソート条件を組み合わせてテスト (例: 'Client 1'で検索し、名前昇順ソート)
        response = self.client.get(reverse('client:client_list'), {'sort': 'name', 'q': 'Client 1', 'page': 1})
        self.assertEqual(response.status_code, 200)
        clients_on_page = response.context['clients'].object_list
        self.assertEqual(clients_on_page[0].name, 'Client 10')
        self.assertEqual(clients_on_page[1].name, 'Client 11')
        self.assertEqual(clients_on_page[2].name, 'Client 12')

        # 8. 検索クエリとソート条件を保持したまま2ページ目に移動 (Client 10, 11, 12 は3件なので、全て1ページ目に表示されるはず)
        self.assertEqual(len(clients_on_page), 3) # 3件のクライアントが検索されることを確認


    def test_client_create_view_get(self):
        response = self.client.get(reverse('client:client_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_form.html')

    def test_client_create_view_post(self):
        data = {
            'corporate_number': '5835678256246', # stdnumが有効と判断する法人番号
            'name': 'New Client',
            'name_furigana': 'ニュークライアントカキクケコ',
            'regist_form_client': 1,
            'basic_contract_date': '2024-01-15'
        }
        response = self.client.post(reverse('client:client_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_list
        client = Client.objects.get(name='New Client')
        self.assertTrue(Client.objects.filter(name='New Client').exists())
        self.assertEqual(str(client.basic_contract_date), '2024-01-15')

    def test_client_detail_view(self):
        response = self.client.get(reverse('client:client_detail', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_detail.html')
        self.assertContains(response, 'Test Client')

    def test_client_update_view_get(self):
        response = self.client.get(reverse('client:client_update', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_form.html')
        self.assertContains(response, 'Test Client')

    def test_client_update_view_post(self):
        data = {
            'corporate_number': self.client_obj.corporate_number, # corporate_numberはuniqueなので既存のものを利用
            'name': 'Updated Client',
            'name_furigana': 'アップデートクライアントサシスセソ',
            'regist_form_client': 1,
            'basic_contract_date': '2024-02-20'
        }
        response = self.client.post(reverse('client:client_update', args=[self.client_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.name, 'Updated Client')
        self.assertEqual(str(self.client_obj.basic_contract_date), '2024-02-20')

    def test_client_delete_view_get(self):
        response = self.client.get(reverse('client:client_delete', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_confirm_delete.html')
        self.assertContains(response, 'Test Client')

    def test_client_delete_view_post(self):
        response = self.client.post(reverse('client:client_delete', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to client_list
        self.assertFalse(Client.objects.filter(pk=self.client_obj.pk).exists())

    def test_client_contacted_create_view_get(self):
        response = self.client.get(reverse('client:client_contacted_create', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_form.html')

    def test_client_contacted_create_view_post(self):
        data = {
            'content': 'Test Contact',
            'detail': 'This is a test contact detail.',
            'contact_type': 1,
            'contacted_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')  # 現在の日時を設定
        }
        response = self.client.post(reverse('client:client_contacted_create', args=[self.client_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        self.assertTrue(ClientContacted.objects.filter(client=self.client_obj, content='Test Contact').exists())

    def test_client_contacted_list_view(self):
        ClientContacted.objects.create(client=self.client_obj, content='Contact 1',contacted_at=timezone.now())
        ClientContacted.objects.create(client=self.client_obj, content='Contact 2',contacted_at=timezone.now())
        response = self.client.get(reverse('client:client_contacted_list', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_list.html')
        self.assertContains(response, 'Contact 1')
        self.assertContains(response, 'Contact 2')

    def test_client_contacted_detail_view(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Detail Test Contact',contacted_at=timezone.now())
        response = self.client.get(reverse('client:client_contacted_detail', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_detail.html')
        self.assertContains(response, 'Detail Test Contact')

    def test_client_contacted_update_view_get(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Original Contact',contacted_at=timezone.now())
        response = self.client.get(reverse('client:client_contacted_update', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_form.html')
        self.assertContains(response, 'Original Contact')

    def test_client_contacted_update_view_post(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Original Contact',contacted_at=timezone.now())
        data = {
            'content': 'Updated Contact',
            'detail': 'Updated detail.',
            'contact_type': 2,
            'contacted_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')  # 現在の日時を設定
        }
        response = self.client.post(reverse('client:client_contacted_update', args=[contacted_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        contacted_obj.refresh_from_db()
        self.assertEqual(contacted_obj.content, 'Updated Contact')

    def test_client_contacted_delete_view_get(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Delete Test Contact',contacted_at=timezone.now())
        response = self.client.get(reverse('client:client_contacted_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_confirm_delete.html')
        self.assertContains(response, 'Delete Test Contact')

    def test_client_contacted_delete_view_post(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Delete Test Contact',contacted_at=timezone.now())
        response = self.client.post(reverse('client:client_contacted_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        self.assertFalse(ClientContacted.objects.filter(pk=contacted_obj.pk).exists())

    def test_client_change_history_list_view(self):
        response = self.client.get(reverse('client:client_change_history_list', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_change_history_list.html')
        self.assertContains(response, 'Test Client')
    
    def test_client_file_list_view(self):
        """クライアントファイル一覧ビューのテスト"""
        # ファイル権限を追加
        from django.contrib.contenttypes.models import ContentType
        from apps.client.models import ClientFile
        content_type = ContentType.objects.get_for_model(ClientFile)
        file_permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*file_permissions)
        
        response = self.client.get(reverse('client:client_file_list', kwargs={'client_pk': self.client_obj.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ファイル一覧')
    
    def test_client_file_create_view(self):
        """クライアントファイル作成ビューのテスト"""
        # ファイル権限を追加
        from django.contrib.contenttypes.models import ContentType
        from apps.client.models import ClientFile
        content_type = ContentType.objects.get_for_model(ClientFile)
        file_permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*file_permissions)
        
        response = self.client.get(reverse('client:client_file_create', kwargs={'client_pk': self.client_obj.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ファイルアップロード')
    
    def test_client_file_create_post(self):
        """クライアントファイル作成POSTのテスト"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.contrib.contenttypes.models import ContentType
        from apps.client.models import ClientFile
        
        # ファイル権限を追加
        content_type = ContentType.objects.get_for_model(ClientFile)
        file_permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*file_permissions)
        
        test_file = SimpleUploadedFile(
            "test_client_upload.txt",
            b"test client upload content",
            content_type="text/plain"
        )
        
        response = self.client.post(
            reverse('client:client_file_create', kwargs={'client_pk': self.client_obj.pk}),
            {
                'file': test_file,
                'description': 'クライアントアップロードテスト'
            }
        )
        
        # 作成後はクライアント詳細画面にリダイレクト
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientFile.objects.filter(client=self.client_obj, description='クライアントアップロードテスト').exists())
    
    def test_client_file_delete_view(self):
        """クライアントファイル削除ビューのテスト"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.contrib.contenttypes.models import ContentType
        from apps.client.models import ClientFile
        
        # ファイル権限を追加
        content_type = ContentType.objects.get_for_model(ClientFile)
        file_permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*file_permissions)
        
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "client_delete_test.txt",
            b"client delete test content",
            content_type="text/plain"
        )
        
        client_file = ClientFile.objects.create(
            client=self.client_obj,
            file=test_file,
            description="クライアント削除テストファイル"
        )
        
        # 削除確認画面のテスト
        response = self.client.get(reverse('client:client_file_delete', kwargs={'pk': client_file.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'client_delete_test.txt')
        self.assertContains(response, '削除しますか？')
        
        # 削除実行のテスト
        response = self.client.post(reverse('client:client_file_delete', kwargs={'pk': client_file.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClientFile.objects.filter(pk=client_file.pk).exists())
    
    def test_client_file_download_view(self):
        """クライアントファイルダウンロードビューのテスト"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.contrib.contenttypes.models import ContentType
        from apps.client.models import ClientFile
        
        # ファイル権限を追加
        content_type = ContentType.objects.get_for_model(ClientFile)
        file_permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*file_permissions)
        
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "client_download_test.txt",
            b"client download test content",
            content_type="text/plain"
        )
        
        client_file = ClientFile.objects.create(
            client=self.client_obj,
            file=test_file,
            description="クライアントダウンロードテストファイル"
        )
        
        response = self.client.get(reverse('client:client_file_download', kwargs={'pk': client_file.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
    
    def test_client_detail_with_files(self):
        """ファイル付きクライアント詳細のテスト"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.contrib.contenttypes.models import ContentType
        from apps.client.models import ClientFile
        
        # ファイル権限を追加
        content_type = ContentType.objects.get_for_model(ClientFile)
        file_permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*file_permissions)
        
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "client_detail_test.txt",
            b"client detail test content",
            content_type="text/plain"
        )
        
        ClientFile.objects.create(
            client=self.client_obj,
            file=test_file,
            description="クライアント詳細テストファイル"
        )
        
        response = self.client.get(reverse('client:client_detail', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'client_detail_test.txt')