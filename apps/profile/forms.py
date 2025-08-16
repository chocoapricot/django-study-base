from django import forms
from .models import StaffProfile


class StaffProfileForm(forms.ModelForm):
    """スタッフプロフィールフォーム"""
    
    sex = forms.ChoiceField(
        choices=[],
        label='性別',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        required=False,
    )
    
    class Meta:
        model = StaffProfile
        fields = [
            'name_last', 'name_first', 'name_kana_last', 'name_kana_first',
            'birth_date', 'sex', 'postal_code', 'address_kana',
            'address1', 'address2', 'address3', 'phone'
        ]
        widgets = {
            'name_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '7'}),
            'address_kana': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address1': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address2': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address3': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dropdownsから性別の選択肢を取得
        from apps.system.settings.models import Dropdowns
        self.fields['sex'].choices = [('', '選択してください')] + [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='sex').order_by('disp_seq')
        ]
        
        # 必須フィールドの設定
        self.fields['name_last'].required = True
        self.fields['name_first'].required = True
        self.fields['name_kana_last'].required = True
        self.fields['name_kana_first'].required = True