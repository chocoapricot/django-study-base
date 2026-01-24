from django import forms
from .models_inquiry import StaffInquiry, StaffInquiryMessage
from apps.connect.models import ConnectStaff
from apps.company.models import Company

class StaffInquiryForm(forms.ModelForm):
    content = forms.CharField(
        label='内容',
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'お問い合わせ内容を入力してください', 'rows': 5})
    )

    class Meta:
        model = StaffInquiry
        fields = ['corporate_number', 'subject']
        widgets = {
            'corporate_number': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '件名を入力してください'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'お問い合わせ内容を入力してください', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.connected_clients_count = 0
        self.single_client_name = ""
        self.single_corporate_number = ""

        if self.user:
            # 承認済みの接続を取得
            connected_corp_numbers = ConnectStaff.objects.filter(
                email=self.user.email,
                status='approved'
            ).values_list('corporate_number', flat=True)
            
            # 法人名を取得
            companies = Company.objects.filter(corporate_number__in=connected_corp_numbers)
            company_dict = {c.corporate_number: c.name for c in companies}
            
            self.connected_clients_count = len(connected_corp_numbers)
            
            if self.connected_clients_count == 1:
                cn = list(connected_corp_numbers)[0]
                self.single_corporate_number = cn
                self.single_client_name = company_dict.get(cn, cn)
                self.fields['corporate_number'].initial = cn
                # １つの場合は選択肢をこれだけにする
                self.fields['corporate_number'].choices = [(cn, self.single_client_name)]
            else:
                choices = [('', '---------')]
                for cn in connected_corp_numbers:
                    name = company_dict.get(cn, cn)
                    choices.append((cn, name))
                
                self.fields['corporate_number'].choices = choices
                self.fields['corporate_number'].widget.choices = choices

    def clean_corporate_number(self):
        corporate_number = self.cleaned_data.get('corporate_number')
        if self.user:
            exists = ConnectStaff.objects.filter(
                email=self.user.email,
                corporate_number=corporate_number,
                status='approved'
            ).exists()
            if not exists:
                raise forms.ValidationError('指定された法人番号への問い合わせ権限がありません。')
        return corporate_number

class StaffInquiryMessageForm(forms.ModelForm):
    class Meta:
        model = StaffInquiryMessage
        fields = ['content', 'is_hidden', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'メッセージを入力してください', 'rows': 3}),
            'is_hidden': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.is_company = kwargs.pop('is_company', False)
        super().__init__(*args, **kwargs)
        if not self.is_company:
            self.fields.pop('attachment')

class StaffInquiryFromAdminForm(forms.ModelForm):
    content = forms.CharField(
        label='内容',
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'メッセージ内容を入力してください', 'rows': 5})
    )

    class Meta:
        model = StaffInquiry
        fields = ['subject', 'attachment']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '件名を入力してください'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'メッセージ内容を入力してください', 'rows': 5}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

class StaffInquiryFilterForm(forms.Form):
    status = forms.ChoiceField(
        label='ステータス',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    def __init__(self, *args, **kwargs):
        is_company_or_admin = kwargs.pop('is_company_or_admin', False)
        super().__init__(*args, **kwargs)

        choices = [('', '---------')] + list(StaffInquiry.STATUS_CHOICES)
        if is_company_or_admin:
            choices.append(('unanswered', '未回答'))
        
        self.fields['status'].choices = choices
