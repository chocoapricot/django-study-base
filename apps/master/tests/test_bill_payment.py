from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.master.models import BillPayment
from apps.master.forms import BillPaymentForm

User = get_user_model()


class BillPaymentModelTest(TestCase):
    """支払いサイトモデルのテスト"""
    
    def setUp(self):
        self.bill_payment = BillPayment.objects.create(
            name='月末締め翌月末払い',
            closing_day=31,
            invoice_months_after=0,
            invoice_day=25,
            payment_months_after=1,
            payment_day=31,
            is_active=True,
            display_order=1
        )
    
    def test_str_method(self):
        """__str__メソッドのテスト"""
        self.assertEqual(str(self.bill_payment), '月末締め翌月末払い')
    
    def test_closing_day_display(self):
        """締め日表示のテスト"""
        self.assertEqual(self.bill_payment.closing_day_display, '月末')
        
        # 通常の日付の場合
        bill_payment = BillPayment.objects.create(
            name='15日締め',
            closing_day=15,
            invoice_months_after=0,
            invoice_day=20,
            payment_months_after=1,
            payment_day=10
        )
        self.assertEqual(bill_payment.closing_day_display, '15日')
    
    def test_invoice_schedule_display(self):
        """請求書スケジュール表示のテスト"""
        self.assertEqual(self.bill_payment.invoice_schedule_display, '当月25日まで')
        
        # 翌月の場合
        bill_payment = BillPayment.objects.create(
            name='翌月請求',
            closing_day=31,
            invoice_months_after=1,
            invoice_day=10,
            payment_months_after=2,
            payment_day=31
        )
        self.assertEqual(bill_payment.invoice_schedule_display, '1か月後10日まで')
    
    def test_payment_schedule_display(self):
        """支払いスケジュール表示のテスト"""
        self.assertEqual(self.bill_payment.payment_schedule_display, '1か月後31日')
        
        # 当月の場合
        bill_payment = BillPayment.objects.create(
            name='当月払い',
            closing_day=15,
            invoice_months_after=0,
            invoice_day=20,
            payment_months_after=0,
            payment_day=25
        )
        self.assertEqual(bill_payment.payment_schedule_display, '当月25日')
    
    def test_full_schedule_display(self):
        """完全スケジュール表示のテスト"""
        expected = '月末締め → 当月25日まで請求書必着 → 1か月後31日支払い'
        self.assertEqual(self.bill_payment.full_schedule_display, expected)
    
    def test_validation_closing_day(self):
        """締め日バリデーションのテスト"""
        bill_payment = BillPayment(
            name='無効な締め日',
            closing_day=32,  # 無効な値
            invoice_months_after=0,
            invoice_day=25,
            payment_months_after=1,
            payment_day=31
        )
        with self.assertRaises(ValidationError):
            bill_payment.clean()
    
    def test_validation_invoice_day(self):
        """請求書必着日バリデーションのテスト"""
        bill_payment = BillPayment(
            name='無効な請求書必着日',
            closing_day=31,
            invoice_months_after=0,
            invoice_day=32,  # 無効な値
            payment_months_after=1,
            payment_day=31
        )
        with self.assertRaises(ValidationError):
            bill_payment.clean()
    
    def test_validation_payment_day(self):
        """支払い日バリデーションのテスト"""
        bill_payment = BillPayment(
            name='無効な支払い日',
            closing_day=31,
            invoice_months_after=0,
            invoice_day=25,
            payment_months_after=1,
            payment_day=32  # 無効な値
        )
        with self.assertRaises(ValidationError):
            bill_payment.clean()
    
    def test_get_active_list(self):
        """有効な支払いサイト一覧取得のテスト"""
        # 無効な支払いサイトを作成
        BillPayment.objects.create(
            name='無効な支払いサイト',
            closing_day=15,
            invoice_months_after=0,
            invoice_day=20,
            payment_months_after=1,
            payment_day=25,
            is_active=False
        )
        
        active_list = BillPayment.get_active_list()
        self.assertEqual(active_list.count(), 1)
        self.assertEqual(active_list.first().name, '月末締め翌月末払い')


class BillPaymentFormTest(TestCase):
    """支払いサイトフォームのテスト"""
    
    def test_valid_form(self):
        """有効なフォームのテスト"""
        form_data = {
            'name': '20日締め翌月10日払い',
            'closing_day': 20,
            'invoice_months_after': 0,
            'invoice_day': 25,
            'payment_months_after': 1,
            'payment_day': 10,
            'is_active': True,
            'display_order': 1
        }
        form = BillPaymentForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_name(self):
        """名前が未入力の場合のテスト"""
        form_data = {
            'closing_day': 20,
            'invoice_months_after': 0,
            'invoice_day': 25,
            'payment_months_after': 1,
            'payment_day': 10,
            'is_active': True,
            'display_order': 1
        }
        form = BillPaymentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class BillPaymentViewTest(TestCase):
    """支払いサイトビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_superuser=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.bill_payment = BillPayment.objects.create(
            name='テスト支払いサイト',
            closing_day=31,
            invoice_months_after=0,
            invoice_day=25,
            payment_months_after=1,
            payment_day=31
        )
    
    def test_bill_payment_list_view(self):
        """支払いサイト一覧ビューのテスト"""
        response = self.client.get(reverse('master:bill_payment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト支払いサイト')
    
    def test_bill_payment_create_view_get(self):
        """支払いサイト作成ビュー（GET）のテスト"""
        response = self.client.get(reverse('master:bill_payment_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '支払いサイト作成')
    
    def test_bill_payment_create_view_post(self):
        """支払いサイト作成ビュー（POST）のテスト"""
        form_data = {
            'name': '新しい支払いサイト',
            'closing_day': 15,
            'invoice_months_after': 0,
            'invoice_day': 20,
            'payment_months_after': 1,
            'payment_day': 25,
            'is_active': True,
            'display_order': 1
        }
        response = self.client.post(reverse('master:bill_payment_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BillPayment.objects.filter(name='新しい支払いサイト').exists())
    
    def test_bill_payment_update_view(self):
        """支払いサイト更新ビューのテスト"""
        response = self.client.get(
            reverse('master:bill_payment_update', kwargs={'pk': self.bill_payment.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト支払いサイト')
    
    def test_bill_payment_delete_view(self):
        """支払いサイト削除ビューのテスト"""
        response = self.client.get(
            reverse('master:bill_payment_delete', kwargs={'pk': self.bill_payment.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト支払いサイト')
        
        # 削除実行
        response = self.client.post(
            reverse('master:bill_payment_delete', kwargs={'pk': self.bill_payment.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BillPayment.objects.filter(pk=self.bill_payment.pk).exists())