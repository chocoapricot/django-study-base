from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.staff.models import Staff
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
import os
import shutil

User = get_user_model()

class StaffFacePhotoTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_superuser(username='admin', password='password', email='admin@example.com', tenant_id=self.company.tenant_id)
        self.client.login(username='admin', password='password')
        
        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            email='yamada@example.com'
        )
        
        # テスト用のメディアディレクトリを作成
        self.test_media_root = os.path.join(settings.BASE_DIR, 'test_media')
        if os.path.exists(self.test_media_root):
            shutil.rmtree(self.test_media_root)
        os.makedirs(os.path.join(self.test_media_root, 'staff_files'))
        
        # settingsを一時的に変更
        self._old_media_root = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = self.test_media_root

    def tearDown(self):
        # settingsを元に戻す
        settings.MEDIA_ROOT = self._old_media_root
        # テスト用のメディアディレクトリを削除
        if os.path.exists(self.test_media_root):
            shutil.rmtree(self.test_media_root)

    def test_has_face_photo_property(self):
        """Staff.has_face_photo プロパティのテスト"""
        # 初期状態では写真は存在しない
        self.assertFalse(self.staff.has_face_photo)
        
        # 写真ファイルを作成
        photo_path = os.path.join(settings.MEDIA_ROOT, 'staff_files', f'{self.staff.pk}.jpg')
        with open(photo_path, 'w') as f:
            f.write('dummy data')
        
        # 写真が存在する状態
        self.assertTrue(self.staff.has_face_photo)
        
        # 写真を削除
        os.remove(photo_path)
        self.assertFalse(self.staff.has_face_photo)

    def test_delete_button_visibility(self):
        """スタッフ詳細画面で削除ボタンの表示・非表示をテスト"""
        # 1. 写真がない場合
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        # 削除ボタンのモーダルターゲットが含まれていないことを確認
        self.assertNotContains(response, 'data-bs-target="#deleteFaceModal"')
        
        # 2. 写真がある場合
        photo_path = os.path.join(settings.MEDIA_ROOT, 'staff_files', f'{self.staff.pk}.jpg')
        with open(photo_path, 'w') as f:
            f.write('dummy data')
            
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        # 削除ボタンのモーダルターゲットが含まれていることを確認
        self.assertContains(response, 'data-bs-target="#deleteFaceModal"')
