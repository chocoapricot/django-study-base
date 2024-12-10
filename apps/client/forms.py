# forms.py
from django import forms
from django.forms import TextInput
from apps.system.dropdowns.models import Dropdowns
from .models import Client
from django.core.exceptions import ValidationError

class ClientForm(forms.ModelForm):

    regist_form_client = forms.ChoiceField(
        choices=[(opt.value, opt.name) for opt in Dropdowns.objects.filter(active=True, category='regist_form_client').order_by('disp_seq')],
        label='登録区分',  # 日本語ラベル
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}) ,
        required=True,
    )

    class Meta:
        model = Client
        fields = ['corporate_number','name','name_furigana',
                  'postal_code','address',  'url', 'memo', 'regist_form_client']
        widgets = {
            'corporate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_furigana': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'phone': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'url': forms.URLInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'regist_form_code': forms.Select(attrs={'class': 'form-control form-control-sm form-select-sm'}),
        }

    # def clean_corporate_number(self):
    #     corporate_number = self.cleaned_data.get('corporate_number')
    #     print(forms.ValidationError)
    #     if Client.objects.filter(corporate_number=corporate_number).exists():  # すでに存在するか確認
    #         raise ValidationError("この法人番号はすでに登録されています。")
    #     return corporate_number