from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.staff.models import Staff
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from apps.master.models import UserParameter
import os
import shutil

User = get_user_model()

class StaffFacePhotoStyleTest(TestCase):
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
        self.test_media_root = os.path.join(settings.BASE_DIR, 'test_media_style')
        if os.path.exists(self.test_media_root):
            shutil.rmtree(self.test_media_root)
        os.makedirs(os.path.join(self.test_media_root, 'staff_files'))
        
        # settingsを一時的に変更
        self._old_media_root = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = self.test_media_root
        
        # パラメータの作成
        self.param, _ = UserParameter.objects.get_or_create(
            pk="STAFF_FACE_PHOTO_STYLE",
            defaults={
                "target_item": "スタッフ顔写真＞表示形式",
                "format": "choice",
                "value": "round",
                "choices": "round:丸,rounded-square:角丸四角,square:四角"
            }
        )

    def tearDown(self):
        # settingsを元に戻す
        settings.MEDIA_ROOT = self._old_media_root
        # テスト用のメディアディレクトリを削除
        if os.path.exists(self.test_media_root):
            shutil.rmtree(self.test_media_root)

    def test_face_photo_style_classes(self):
        """顔写真の表示形式によるCSSクラスの切り替えテスト"""
        
        # 1. 写真がない場合（パラメータに関わらず round 固定）
        for style in ['round', 'rounded-square', 'square']:
            self.param.value = style
            self.param.save()
            
            response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
            # 写真がないので rounded-circle が使われるはず
            self.assertContains(response, 'face-photo-container rounded-circle')
            # img-fluid ではなく、div のプレースホルダーが表示される
            self.assertContains(response, 'rounded-circle')
            self.assertContains(response, self.staff.initials)
            self.assertNotContains(response, 'img-fluid')

        # 2. 写真がある場合
        photo_path = os.path.join(settings.MEDIA_ROOT, 'staff_files', f'{self.staff.pk}.jpg')
        with open(photo_path, 'w') as f:
            f.write('dummy data')
            
        # 2-1. round (丸)
        self.param.value = 'round'
        self.param.save()
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertContains(response, 'face-photo-container rounded-circle')
        
        # 2-2. rounded-square (角丸四角)
        self.param.value = 'rounded-square'
        self.param.save()
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertContains(response, 'face-photo-container rounded')
        
        self.param.value = 'square'
        self.param.save()
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertContains(response, 'face-photo-container rounded-0')

    def test_face_photo_style_classes_in_list(self):
        """一覧画面での顔写真表示形式によるCSSクラスの切り替えテスト"""
        
        # 1. 写真がない場合（ round 固定）
        self.param.value = 'square'
        self.param.save()
        response = self.client.get(reverse('staff:staff_list'))
        # 写真がないので rounded-circle
        self.assertContains(response, 'rounded-circle')
        self.assertContains(response, self.staff.initials)
        self.assertNotContains(response, 'img-fluid')

        # 2. 写真がある場合
        photo_path = os.path.join(settings.MEDIA_ROOT, 'staff_files', f'{self.staff.pk}.jpg')
        with open(photo_path, 'w') as f:
            f.write('dummy data')
            
        # 2-1. square (四角)
        self.param.value = 'square'
        self.param.save()
        response = self.client.get(reverse('staff:staff_list'))
        self.assertContains(response, 'img-fluid rounded-0')
