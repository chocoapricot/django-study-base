from django.test import TestCase
from django.utils import timezone
from apps.client.models import Client
from apps.contract.models import ClientContract, ClientContractNumber
from apps.contract.utils import generate_client_contract_number
from apps.master.models import ContractPattern

class ClientContractNumberingTest(TestCase):
    def setUp(self):
        """テストに必要な初期データを作成"""
        self.client = Client.objects.create(
            name='テストクライアント',
            name_furigana='テストクライアント',
            corporate_number='1234567890123'
        )
        self.pattern = ContractPattern.objects.create(
            name='テストパターン',
            domain='10',
        )
        self.contract = ClientContract.objects.create(
            client=self.client,
            contract_name='テスト契約',
            start_date=timezone.now().date(),
            contract_pattern=self.pattern,
        )

    def test_generate_first_number_with_client_code(self):
        """初回採番のテスト（クライアントコード使用）"""
        number = generate_client_contract_number(self.contract)
        year_month = self.contract.start_date.strftime('%Y%m')
        client_code = self.client.client_code
        self.assertEqual(number, f"{client_code}-{year_month}-0001")

        # データベースに記録されているか確認
        num_obj = ClientContractNumber.objects.get(
            client_code=client_code,
            year_month=year_month
        )
        self.assertEqual(num_obj.last_number, 1)

    def test_generate_second_number_with_client_code(self):
        """2回目の採番テスト（クライアントコード使用）"""
        # 1回目の採番
        generate_client_contract_number(self.contract)

        # 2回目の採番
        number = generate_client_contract_number(self.contract)
        year_month = self.contract.start_date.strftime('%Y%m')
        client_code = self.client.client_code
        self.assertEqual(number, f"{client_code}-{year_month}-0002")

        # データベースに記録されているか確認
        num_obj = ClientContractNumber.objects.get(
            client_code=client_code,
            year_month=year_month
        )
        self.assertEqual(num_obj.last_number, 2)

    def test_numbering_for_different_month_with_client_code(self):
        """月が変わった場合の採番テスト（クライアントコード使用）"""
        # 来月の契約を作成
        next_month_date = self.contract.start_date + timezone.timedelta(days=31)
        next_month_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='来月のテスト契約',
            start_date=next_month_date,
            contract_pattern=self.pattern,
        )

        number = generate_client_contract_number(next_month_contract)
        year_month = next_month_date.strftime('%Y%m')
        client_code = self.client.client_code
        self.assertEqual(number, f"{client_code}-{year_month}-0001")

        # データベースに記録されているか確認
        num_obj = ClientContractNumber.objects.get(
            client_code=client_code,
            year_month=year_month
        )
        self.assertEqual(num_obj.last_number, 1)

    def test_no_client_code(self):
        """クライアントコードが生成できない場合にValueErrorが発生するか"""
        self.client.corporate_number = None
        self.client.save()
        # client_code プロパティが空文字列を返すことを確認
        self.assertEqual(self.client.client_code, "")
        with self.assertRaises(ValueError):
            generate_client_contract_number(self.contract)
