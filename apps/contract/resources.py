"""
契約データのエクスポート機能用リソースクラス

django-import-exportライブラリを使用して、契約データをCSV/Excel形式で出力する。
各dehydrateメソッドは、エクスポート時にデータベースの値を表示用の値に変換するために使用される。

使用箇所:
- クライアント契約一覧画面の「CSV出力」「Excel出力」ボタン
- スタッフ契約一覧画面の「CSV出力」「Excel出力」ボタン
"""
from import_export import resources, fields
from .models import ClientContract, StaffContract

class ClientContractResource(resources.ModelResource):
    """
    クライアント契約データのCSV/Excelエクスポート用リソースクラス
    django-import-exportライブラリを使用してデータ出力を行う
    """
    client_name = fields.Field(attribute='client__name', column_name='クライアント名')
    contract_status_display = fields.Field(column_name='契約ステータス')

    class Meta:
        model = ClientContract
        fields = ('id', 'contract_name', 'client_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')
        export_order = ('id', 'contract_name', 'client_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')

    def dehydrate_contract_status_display(self, contract):
        """
        CSV/Excelエクスポート時に契約ステータスの表示名を出力するメソッド
        django-import-exportライブラリのdehydrate機能を使用
        ステータスコード（'1', '5'など）を日本語表示名（'作成中', '申請中'など）に変換
        """
        from apps.system.settings.models import Dropdowns
        return Dropdowns.get_display_name('contract_status', contract.contract_status)

class StaffContractResource(resources.ModelResource):
    """
    スタッフ契約データのCSV/Excelエクスポート用リソースクラス
    django-import-exportライブラリを使用してデータ出力を行う
    """
    staff_name = fields.Field(column_name='スタッフ名')
    contract_status_display = fields.Field(column_name='契約ステータス')

    class Meta:
        model = StaffContract
        fields = ('id', 'contract_name', 'staff_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')
        export_order = ('id', 'contract_name', 'staff_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')

    def dehydrate_staff_name(self, contract):
        """スタッフ名を「姓 名」形式で出力"""
        return contract.staff.name

    def dehydrate_contract_status_display(self, contract):
        """
        CSV/Excelエクスポート時に契約ステータスの表示名を出力するメソッド
        django-import-exportライブラリのdehydrate機能を使用
        ステータスコード（'1', '5'など）を日本語表示名（'作成中', '申請中'など）に変換
        """
        from apps.system.settings.models import Dropdowns
        return Dropdowns.get_display_name('contract_status', contract.contract_status)
