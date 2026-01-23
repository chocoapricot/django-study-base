from django import forms
from django.core.mail import send_mail
from django.conf import settings
from apps.system.logs.models import MailLog
from apps.client.models import ClientContacted, ClientUser
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.system.notifications.models import Notification


class ClientUserMailForm(forms.Form):
    """クライアント担当者メール送信フォーム"""
    
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
    
    send_notification = forms.BooleanField(
        label='通知を送る',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='チェックを入れると、クライアントのマイページに通知を表示します。'
    )
    
    def __init__(self, client_user=None, user=None, *args, **kwargs):
        self.client_user = client_user
        self.user = user
        super().__init__(*args, **kwargs)
        
        if client_user and client_user.email:
            self.fields['to_email'].initial = client_user.email
    
    def clean_to_email(self):
        """宛先メールアドレスのバリデーション"""
        to_email = self.cleaned_data.get('to_email')
        if self.client_user and to_email != self.client_user.email:
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
            
            # クライアント連絡履歴に保存（常に保存）
            if self.client_user and self.client_user.client:
                ClientContacted.objects.create(
                    client=self.client_user.client,
                    department=self.client_user.department,
                    user=self.client_user,
                    contacted_at=timezone.now(),
                    content=f"メール送信: {subject}",
                    detail=body,
                    contact_type=self._get_contact_type_value('email'),
                    created_by=self.user,
                    updated_by=self.user
                )
            
            
            # 通知を作成（チェックされている場合）
            if self.cleaned_data.get('send_notification'):
                User = get_user_model()
                # 担当者のメールアドレスに紐づくユーザーを探す
                client_user_obj = User.objects.filter(email=self.client_user.email).first()
                if client_user_obj:
                    Notification.objects.create(
                        user=client_user_obj,
                        title=subject,
                        message=body,
                        notification_type='general', # 一般
                        link_url=None, # 必要があれば詳細画面へのリンクを入れる
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


class ClientMailForm(forms.Form):
    """クライアントメール送信フォーム (予定詳細用)"""
    
    to_user = forms.ModelChoiceField(
        queryset=ClientUser.objects.none(),
        label='宛先担当者',
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
        }),
        required=True
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

    send_notification = forms.BooleanField(
        label='通知を送る',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='チェックを入れると、クライアントのマイページに通知を表示します。'
    )
    
    def __init__(self, client=None, user=None, *args, **kwargs):
        self.client = client
        self.user = user  # ログインユーザー
        super().__init__(*args, **kwargs)
        
        if client:
            # メールアドレスが設定されている担当者のみ抽出
            self.fields['to_user'].queryset = ClientUser.objects.filter(
                client=client,
                email__isnull=False
            ).exclude(email='').order_by('display_order', 'name_last', 'name_first')

    def send_mail(self):
        """メール送信処理"""
        if not self.is_valid():
            return False, "フォームデータが無効です。"
        
        to_user = self.cleaned_data['to_user']
        to_email = to_user.email
        subject = self.cleaned_data['subject']
        body = self.cleaned_data['body']
        
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
            ClientContacted.objects.create(
                client=self.client,
                department=to_user.department,
                user=to_user,
                contacted_at=timezone.now(),
                content=f"メール送信: {subject}",
                detail=body,
                contact_type=self._get_contact_type_value(),
                created_by=self.user,
                updated_by=self.user
            )

            # 通知を作成（チェックされている場合）
            if self.cleaned_data.get('send_notification'):
                User = get_user_model()
                # 担当者のメールアドレスに紐づくユーザーを探す
                client_user_obj = User.objects.filter(email=to_email).first()
                if client_user_obj:
                    Notification.objects.create(
                        user=client_user_obj,
                        title=subject,
                        message=body,
                        notification_type='general', # 一般
                        link_url=None, # 必要があれば詳細画面へのリンクを入れる
                    )
            
            return True, "メールを送信しました。"
            
        except Exception as e:
            # 送信失敗時の処理
            mail_log.status = 'failed'
            mail_log.error_message = str(e)
            mail_log.save()
            
            return False, f"メール送信に失敗しました: {str(e)}"
    
    def _get_contact_type_value(self):
        """連絡種別のキーから値を取得"""
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
        
        return 1