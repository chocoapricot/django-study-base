from django import forms
from django.core.mail import send_mail
from django.conf import settings
from apps.system.logs.models import MailLog
from apps.staff.models import StaffContacted
from django.utils import timezone


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
    
    contact_type = forms.ChoiceField(
        label='連絡種別',
        choices=CONTACT_TYPE_CHOICES,
        initial='email',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    save_to_contact_history = forms.BooleanField(
        label='連絡履歴に保存',
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
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
        contact_type = self.cleaned_data['contact_type']
        save_to_history = self.cleaned_data['save_to_contact_history']
        
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
            
            # 連絡履歴に保存
            if save_to_history and self.staff:
                StaffContacted.objects.create(
                    staff=self.staff,
                    contacted_at=timezone.now(),
                    content=f"メール送信: {subject}",
                    detail=body,
                    contact_type=self._get_contact_type_value(contact_type),
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