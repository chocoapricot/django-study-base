from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Client
from apps.master.models import BillPayment, ClientRegistStatus


class ClientResource(resources.ModelResource):
    """クライアントデータのインポート/エクスポート用リソース"""
    
    # 登録区分の表示名を取得
    regist_status_display = fields.Field(
        column_name='Registration Type',
        attribute='regist_status__name',
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
            'regist_status_display',
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
            'regist_status_display',
            'basic_contract_date',
            'payment_site_display',
            'created_at',
            'updated_at',
        )
    
    def dehydrate_regist_status_display(self, client):
        """登録区分の表示名を取得"""
        if client.regist_status:
            return client.regist_status.name
        return ''