import os
import tempfile
import hashlib
from datetime import date
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.contract.models import (
    ClientContract, ClientContractPrint, 
    StaffContract, StaffContractPrint,
    ContractAssignment, ContractAssignmentHakenPrint
)
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import JobCategory, ContractPattern

User = get_user_model()


class FileHashTestCase(TestCase):
    """PDFファイルのSHA256ハッシュ値計算機能のテストケース"""

    def setUp(self):
        """テスト用データの準備"""
        # テスト用ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # テスト用クライアント作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用マスターデータ作成
        self.job_category = JobCategory.objects.create(name='エンジニア', is_active=True)
        self.client_pattern = ContractPattern.objects.create(name='クライアント向け基本契約', domain='10', is_active=True)
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)
        
        # テスト用クライアント契約作成
        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テスト契約',
            job_category=self.job_category,
            contract_pattern=self.client_pattern,
            start_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='テストスタッフ契約',
            job_category=self.job_category,
            contract_pattern=self.staff_pattern,
            start_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用PDFファイル内容
        self.pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000173 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n253\n%%EOF'
        
        # 期待されるハッシュ値を事前計算
        self.expected_hash = hashlib.sha256(self.pdf_content).hexdigest()

    def test_client_contract_print_hash_calculation(self):
        """ClientContractPrintのハッシュ値計算テスト"""
        # PDFファイルを作成
        pdf_file = SimpleUploadedFile(
            "test_contract.pdf",
            self.pdf_content,
            content_type="application/pdf"
        )
        
        # ClientContractPrintインスタンス作成
        print_record = ClientContractPrint.objects.create(
            client_contract=self.client_contract,
            print_type='10',
            printed_by=self.user,
            pdf_file=pdf_file,
            document_title='テスト契約書'
        )
        
        # ハッシュ値が正しく計算されているか確認
        self.assertEqual(print_record.file_hash, self.expected_hash)
        self.assertIsNotNone(print_record.file_hash)
        self.assertEqual(len(print_record.file_hash), 64)  # SHA256は64文字

    def test_staff_contract_print_hash_calculation(self):
        """StaffContractPrintのハッシュ値計算テスト"""
        # PDFファイルを作成
        pdf_file = SimpleUploadedFile(
            "test_staff_contract.pdf",
            self.pdf_content,
            content_type="application/pdf"
        )
        
        # StaffContractPrintインスタンス作成
        print_record = StaffContractPrint.objects.create(
            staff_contract=self.staff_contract,
            printed_by=self.user,
            pdf_file=pdf_file,
            document_title='テストスタッフ契約書'
        )
        
        # ハッシュ値が正しく計算されているか確認
        self.assertEqual(print_record.file_hash, self.expected_hash)
        self.assertIsNotNone(print_record.file_hash)
        self.assertEqual(len(print_record.file_hash), 64)

    def test_assignment_haken_print_hash_calculation(self):
        """ContractAssignmentHakenPrintのハッシュ値計算テスト"""
        # ContractAssignmentを作成
        assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            created_by=self.user,
            updated_by=self.user
        )
        
        # PDFファイルを作成
        pdf_file = SimpleUploadedFile(
            "test_assignment.pdf",
            self.pdf_content,
            content_type="application/pdf"
        )
        
        # ContractAssignmentHakenPrintインスタンス作成
        print_record = ContractAssignmentHakenPrint.objects.create(
            contract_assignment=assignment,
            print_type='10',
            printed_by=self.user,
            pdf_file=pdf_file,
            document_title='テスト就業条件明示書'
        )
        
        # ハッシュ値が正しく計算されているか確認
        self.assertEqual(print_record.file_hash, self.expected_hash)
        self.assertIsNotNone(print_record.file_hash)
        self.assertEqual(len(print_record.file_hash), 64)

    def test_no_file_no_hash(self):
        """ファイルがない場合はハッシュ値が設定されないことを確認"""
        # ファイルなしでClientContractPrintを作成
        print_record = ClientContractPrint.objects.create(
            client_contract=self.client_contract,
            print_type='10',
            printed_by=self.user,
            document_title='ファイルなしテスト'
        )
        
        # ハッシュ値が設定されていないことを確認
        self.assertIsNone(print_record.file_hash)

    def test_hash_not_recalculated_if_exists(self):
        """既にハッシュ値が設定されている場合は再計算されないことを確認"""
        # PDFファイルを作成
        pdf_file = SimpleUploadedFile(
            "test_contract.pdf",
            self.pdf_content,
            content_type="application/pdf"
        )
        
        # 事前にハッシュ値を設定してインスタンス作成
        existing_hash = "existing_hash_value"
        print_record = ClientContractPrint(
            client_contract=self.client_contract,
            print_type='10',
            printed_by=self.user,
            pdf_file=pdf_file,
            document_title='既存ハッシュテスト',
            file_hash=existing_hash
        )
        print_record.save()
        
        # 既存のハッシュ値が保持されていることを確認
        self.assertEqual(print_record.file_hash, existing_hash)
        self.assertNotEqual(print_record.file_hash, self.expected_hash)

    def test_different_files_different_hashes(self):
        """異なるファイルは異なるハッシュ値を持つことを確認"""
        # 1つ目のPDFファイル
        pdf_file1 = SimpleUploadedFile(
            "test1.pdf",
            self.pdf_content,
            content_type="application/pdf"
        )
        
        # 2つ目のPDFファイル（内容が異なる）
        different_content = self.pdf_content + b'\nAdditional content'
        pdf_file2 = SimpleUploadedFile(
            "test2.pdf",
            different_content,
            content_type="application/pdf"
        )
        
        # 1つ目のPrintレコード作成
        print_record1 = ClientContractPrint.objects.create(
            client_contract=self.client_contract,
            print_type='10',
            printed_by=self.user,
            pdf_file=pdf_file1,
            document_title='テスト1'
        )
        
        # 2つ目のPrintレコード作成
        print_record2 = ClientContractPrint.objects.create(
            client_contract=self.client_contract,
            print_type='20',
            printed_by=self.user,
            pdf_file=pdf_file2,
            document_title='テスト2'
        )
        
        # 異なるハッシュ値を持つことを確認
        self.assertNotEqual(print_record1.file_hash, print_record2.file_hash)
        self.assertEqual(print_record1.file_hash, self.expected_hash)
        self.assertEqual(print_record2.file_hash, hashlib.sha256(different_content).hexdigest())