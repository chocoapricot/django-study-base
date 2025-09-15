from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Client
from apps.master.models import BillPayment
from apps.system.settings.models import Dropdowns


class ClientResource(resources.ModelResource):
    """クライアントデータのインポート/エクスポート用リソース"""
    
    # 登録区分の表示名を取得
    client_regist_status_display = fields.Field(
        column_name='Registration Type',
        attribute='client_regist_status',
        readonly=True
    )
    
    # 支払いサイトの表示名を取得
    payment_site_display = fields.Field(
        column_name='Payment Site',
        attribute='payment_site__name',
        readonly=True
    )
    
    class Meta:
        model = Client
        fields = (
            'id',
            'corporate_number',
            'name',
            'name_furigana',
            'postal_code',
            'address_kana',
            'address',
            'memo',
            'client_regist_status_display',
            'basic_contract_date',
            'payment_site_display',
            'created_at',
            'updated_at',
        )
        export_order = (
            'id',
            'corporate_number',
            'name',
            'name_furigana',
            'postal_code',
            'address_kana',
            'address',
            'memo',
            'client_regist_status_display',
            'basic_contract_date',
            'payment_site_display',
            'created_at',
            'updated_at',
        )
    
    def dehydrate_client_regist_status_display(self, client):
        """登録区分の表示名を取得"""
        if client.client_regist_status:
            try:
                dropdown = Dropdowns.objects.get(
                    category='client_regist_status',
                    value=client.client_regist_status,
                    active=True
                )
                return dropdown.name
            except Dropdowns.DoesNotExist:
                return str(client.client_regist_status)
        return ''