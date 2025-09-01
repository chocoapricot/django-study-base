from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Client
from apps.master.models import BillPayment
from apps.system.settings.models import Dropdowns


class ClientResource(resources.ModelResource):
    """クライアントデータのインポート/エクスポート用リソース"""
    
    # 登録区分の表示名を取得
    regist_form_client_display = fields.Field(
        column_name='Registration Type',
        attribute='regist_form_client',
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
            'regist_form_client_display',
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
            'regist_form_client_display',
            'basic_contract_date',
            'payment_site_display',
            'created_at',
            'updated_at',
        )
    
    def dehydrate_regist_form_client_display(self, client):
        """登録区分の表示名を取得"""
        if client.regist_form_client:
            try:
                dropdown = Dropdowns.objects.get(
                    category='regist_form_client',
                    value=client.regist_form_client,
                    active=True
                )
                return dropdown.name
            except Dropdowns.DoesNotExist:
                return str(client.regist_form_client)
        return ''