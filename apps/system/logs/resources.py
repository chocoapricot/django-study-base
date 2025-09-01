from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import AppLog, MailLog
from django.contrib.auth import get_user_model

User = get_user_model()

class AppLogResource(resources.ModelResource):
    """アプリケーション操作ログのエクスポート用リソース"""
    user = fields.Field(
        column_name='ユーザー',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    action_display = fields.Field(
        column_name='操作',
        attribute='action_display_name',
        readonly=True
    )
    timestamp = fields.Field(
        column_name='日時',
        attribute='timestamp',
    )
    model_name = fields.Field(
        column_name='モデル',
        attribute='model_name',
    )
    object_id = fields.Field(
        column_name='対象ID',
        attribute='object_id',
    )
    object_repr = fields.Field(
        column_name='内容',
        attribute='object_repr',
    )

    class Meta:
        model = AppLog
        fields = ('timestamp', 'user', 'action_display', 'model_name', 'object_id', 'object_repr')
        export_order = fields


class MailLogResource(resources.ModelResource):
    """メール送信ログのエクスポート用リソース"""
    mail_type_display = fields.Field(
        column_name='種別',
        attribute='mail_type_display_name',
        readonly=True
    )
    status_display = fields.Field(
        column_name='状況',
        attribute='status_display_name',
        readonly=True
    )
    created_at = fields.Field(
        column_name='送信日時',
        attribute='created_at',
    )
    to_email = fields.Field(
        column_name='受信者',
        attribute='to_email',
    )
    subject = fields.Field(
        column_name='件名',
        attribute='subject',
    )

    class Meta:
        model = MailLog
        fields = ('created_at', 'mail_type_display', 'to_email', 'subject', 'status_display')
        export_order = fields
