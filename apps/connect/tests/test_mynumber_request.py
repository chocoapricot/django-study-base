from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.profile.models import ProfileMynumber
from apps.connect.models import ConnectStaff, MynumberRequest

User = get_user_model()

class MynumberRequestSignalTest(TestCase):
    def setUp(self):
        # テスト用のユーザーを作成
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='testuser1@example.com',
            password='password'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='testuser2@example.com',
            password='password'
        )

        # 承認済みの接続を作成
        self.connect_staff1 = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email=self.user1.email,
            status='approved'
        )
        # 別のユーザーの承認済み接続
        self.connect_staff2 = ConnectStaff.objects.create(
            corporate_number='1234567890124',
            email=self.user2.email,
            status='approved'
        )
        # 未承認の接続
        self.connect_staff_pending = ConnectStaff.objects.create(
            corporate_number='1234567890125',
            email=self.user1.email,
            status='pending'
        )

    def test_request_creation_on_mynumber_create(self):
        """
        ProfileMynumber作成時にMynumberRequestが作成されることをテスト
        """
        # ProfileMynumberを作成
        profile_mynumber = ProfileMynumber.objects.create(
            user=self.user1,
            mynumber='123456789012'
        )

        # MynumberRequestが1つ作成されていることを確認
        self.assertEqual(MynumberRequest.objects.count(), 1)
        request = MynumberRequest.objects.first()
        self.assertEqual(request.connect_staff, self.connect_staff1)
        self.assertEqual(request.profile_mynumber, profile_mynumber)
        self.assertEqual(request.status, 'pending')

    def test_request_recreation_on_mynumber_update(self):
        """
        ProfileMynumber更新時にMynumberRequestが再作成されることをテスト
        """
        # 最初にProfileMynumberを作成
        profile_mynumber = ProfileMynumber.objects.create(
            user=self.user1,
            mynumber='123456789012'
        )
        self.assertEqual(MynumberRequest.objects.count(), 1)
        original_request = MynumberRequest.objects.first()
        original_request_id = original_request.id

        # ProfileMynumberを更新
        profile_mynumber.mynumber = '210987654321'
        profile_mynumber.save()

        # 古いリクエストが削除され、新しいリクエストが作成されたことを確認
        self.assertFalse(MynumberRequest.objects.filter(id=original_request_id).exists())
        self.assertEqual(MynumberRequest.objects.count(), 1)
        updated_request = MynumberRequest.objects.first()
        self.assertEqual(updated_request.connect_staff, self.connect_staff1)
        self.assertEqual(updated_request.profile_mynumber, profile_mynumber)

    def test_no_request_if_no_approved_connection(self):
        """
        承認済みの接続がない場合、MynumberRequestが作成されないことをテスト
        """
        # 承認済みの接続がないユーザーでProfileMynumberを作成
        user_no_connection = User.objects.create_user(
            username='nouser', email='nouser@example.com', password='password'
        )
        ProfileMynumber.objects.create(
            user=user_no_connection,
            mynumber='111122223333'
        )

        # MynumberRequestが作成されていないことを確認
        self.assertEqual(MynumberRequest.objects.count(), 0)

    def test_multiple_connections(self):
        """
        一人のユーザーに複数の承認済み接続がある場合のテスト
        """
        # 同じユーザーにもう一つ承認済み接続を追加
        ConnectStaff.objects.create(
            corporate_number='9998887776665',
            email=self.user1.email,
            status='approved'
        )

        # ProfileMynumberを作成
        ProfileMynumber.objects.create(
            user=self.user1,
            mynumber='123456789012'
        )

        # 2つのMynumberRequestが作成されていることを確認
        self.assertEqual(MynumberRequest.objects.count(), 2)
        self.assertEqual(MynumberRequest.objects.filter(profile_mynumber__user=self.user1).count(), 2)
