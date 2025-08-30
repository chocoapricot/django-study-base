from django import forms
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from apps.system.logs.models import MailLog
from apps.staff.models import StaffContacted, Staff
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.company.models import Company


class StaffMailForm(forms.Form):
    """スタッフメール送信フォーム"""
    
    CONTACT_TYPE_CHOICES = [
        ('email', 'メール'),
        ('notification', '通知'),
        ('reminder', 'リマインダー'),
        ('general', '一般連絡'),
    ]
    
    to_email = forms.EmailField(
        label='宛先',
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-sm',
            'readonly': True
        })
    )
    
    subject = forms.CharField(
        label='件名',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': '件名を入力してください'
        })
    )
    
    body = forms.CharField(
        label='本文',
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm',
            'rows': 10,
            'placeholder': 'メール本文を入力してください'
        })
    )
    

    
    def __init__(self, staff=None, user=None, *args, **kwargs):
        self.staff = staff
        self.user = user
        super().__init__(*args, **kwargs)
        
        if staff and staff.email:
            self.fields['to_email'].initial = staff.email
    
    def clean_to_email(self):
        """宛先メールアドレスのバリデーション"""
        to_email = self.cleaned_data.get('to_email')
        if self.staff and to_email != self.staff.email:
            raise forms.ValidationError('宛先メールアドレスが正しくありません。')
        return to_email
    
    def send_mail(self):
        """メール送信処理"""
        if not self.is_valid():
            return False, "フォームデータが無効です。"
        
        subject = self.cleaned_data['subject']
        body = self.cleaned_data['body']
        to_email = self.cleaned_data['to_email']
        
        # メールログを作成
        mail_log = MailLog.objects.create(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_email=to_email,
            mail_type='general',
            subject=subject,
            body=body,
            status='pending',
            created_by=self.user,
            updated_by=self.user
        )
        
        try:
            # メール送信
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            
            # 送信成功時の処理
            mail_log.status = 'sent'
            mail_log.sent_at = timezone.now()
            mail_log.save()
            
            # 連絡履歴に保存（常に保存）
            if self.staff:
                StaffContacted.objects.create(
                    staff=self.staff,
                    contacted_at=timezone.now(),
                    content=f"メール送信: {subject}",
                    detail=body,
                    contact_type=self._get_contact_type_value('email'),
                    created_by=self.user,
                    updated_by=self.user
                )
            
            return True, "メールを送信しました。"
            
        except Exception as e:
            # 送信失敗時の処理
            mail_log.status = 'failed'
            mail_log.error_message = str(e)
            mail_log.save()
            
            return False, f"メール送信に失敗しました: {str(e)}"
    
    def _get_contact_type_value(self, contact_type_key):
        """連絡種別のキーから値を取得"""
        # システム設定のDropdownsから連絡種別の値を取得
        from apps.system.settings.models import Dropdowns
        try:
            dropdown = Dropdowns.objects.filter(
                category='contact_type',
                name__icontains='メール'
            ).first()
            if dropdown:
                return int(dropdown.value)
        except (ValueError, AttributeError):
            pass
        
        # デフォルト値を返す
        return 1


class ConnectionRequestMailForm:
    """接続申請メール送信フォーム"""

    def __init__(self, staff, user):
        self.staff = staff
        self.user = user

    def send_mail(self):
        """メール送信処理"""
        User = get_user_model()
        user_exists = User.objects.filter(email=self.staff.email).exists()

        if user_exists:
            subject_template_name = 'staff/email/connect_request_existing_user_subject.txt'
            message_template_name = 'staff/email/connect_request_existing_user_message.txt'
        else:
            subject_template_name = 'staff/email/connect_request_new_user_subject.txt'
            message_template_name = 'staff/email/connect_request_new_user_message.txt'

        company = Company.objects.first()
        company_name = company.name if company else '貴社'

        login_url = settings.LOGIN_URL
        signup_url = reverse('account_signup')

        context = {
            'staff_name': self.staff.name,
            'company_name': company_name,
            'login_url': login_url,
            'signup_url': signup_url,
        }
        subject = render_to_string(subject_template_name, context).strip()
        body = render_to_string(message_template_name, context)

        # メールログを作成
        mail_log = MailLog.objects.create(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_email=self.staff.email,
            mail_type='notification',
            subject=subject,
            body=body,
            status='pending',
            created_by=self.user,
            updated_by=self.user
        )

        try:
            # メール送信
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.staff.email],
                fail_silently=False,
            )

            # 送信成功時の処理
            mail_log.status = 'sent'
            mail_log.sent_at = timezone.now()
            mail_log.save()

            # 連絡履歴に保存
            StaffContacted.objects.create(
                staff=self.staff,
                contacted_at=timezone.now(),
                content=subject,
                detail=body,
                contact_type=50, # メール配信
                created_by=self.user,
                updated_by=self.user
            )

            return True, "メールを送信しました。"

        except Exception as e:
            # 送信失敗時の処理
            mail_log.status = 'failed'
            mail_log.error_message = str(e)
            mail_log.save()

            return False, f"メール送信に失敗しました: {str(e)}"