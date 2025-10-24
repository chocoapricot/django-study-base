from django import forms
from .models_phrase import PhraseTemplate


class PhraseTemplateForm(forms.ModelForm):
    """汎用文言テンプレートフォーム"""
    
    class Meta:
        model = PhraseTemplate
        fields = ['category', 'content', 'is_active', 'display_order']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 全てのフィールドを必須にする（is_activeは除く）
        for field_name, field in self.fields.items():
            if field_name != 'is_active':
                field.required = True
        
        # 表示順のデフォルト値を設定
        if not self.instance.pk:
            self.fields['display_order'].initial = 0