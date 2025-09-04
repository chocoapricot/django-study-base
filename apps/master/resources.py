from import_export import resources, fields

class AgreedStaffResource(resources.Resource):
    """同意済みスタッフデータのエクスポート用リソース"""
    staff_name = fields.Field(column_name='氏名')
    staff_email = fields.Field(column_name='メールアドレス')
    agreed_at = fields.Field(column_name='同意日時')

    class Meta:
        export_order = ('staff_name', 'staff_email', 'agreed_at')

    def dehydrate_staff_name(self, obj):
        return obj['staff'].name

    def dehydrate_staff_email(self, obj):
        return obj['staff'].email

    def dehydrate_agreed_at(self, obj):
        return obj['agreed_at'].strftime('%Y-%m-%d %H:%M:%S')
