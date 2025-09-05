from django.db import migrations

def populate_mail_templates(apps, schema_editor):
    MailTemplate = apps.get_model('master', 'MailTemplate')

    templates_to_migrate = {
        'password_reset_key': {
            'subject': 'パスワードリセットのご案内',
            'body': '{{ user.get_full_name }}様\n\nパスワードのリセットを受け付けました。\n以下のリンクからパスワードの再設定を行ってください。\n\n{{ password_reset_url }}\n\nよろしくお願いいたします。',
            'remarks': 'パスワードリセット用のメールテンプレート。'
        },
        'connect_request_existing_user': {
            'subject': '【{{ company_name }}】接続申請のお知らせ',
            'body': '{{ staff_name }}様\n\n{{ company_name }}の管理者より、システムへの接続申請がありました。\n\n下記URLよりログインして、申請を承認してください。\n\n{{ login_url }}\n\nよろしくお願いいたします。',
            'remarks': '既存ユーザーへの接続申請メール。'
        },
        'connect_request_new_user': {
            'subject': '【{{ company_name }}】アカウント登録と接続申請のお知らせ',
            'body': '{{ staff_name }}様\n\n{{ company_name }}の管理者より、システムへの接続申請がありました。\n\nシステムを利用するにはアカウント登録が必要です。\n下記URLよりアカウント登録を行い、その後、再度ログインして申請を承認してください。\n\n{{ signup_url }}\n\nよろしくお願いいたします。',
            'remarks': '新規ユーザーへの接続申請メール。'
        },
        'disconnection_notification': {
            'subject': '【{{ company_name }}】接続解除のお知らせ',
            'body': '{{ staff_name }}様\n\n{{ company_name }}の管理者により、システムとの接続が解除されました。\n\nご了承ください。',
            'remarks': '接続解除通知メール。'
        }
    }

    for key, data in templates_to_migrate.items():
        MailTemplate.objects.update_or_create(
            template_key=key,
            defaults={
                'subject': data['subject'],
                'body': data['body'],
                'remarks': data['remarks']
            }
        )

class Migration(migrations.Migration):

    dependencies = [
        ('master', '0018_mailtemplate'),
    ]

    operations = [
        migrations.RunPython(populate_mail_templates),
    ]
