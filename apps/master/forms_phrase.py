from django import forms
from .models_phrase import PhraseTemplate, PhraseTemplateTitle


class PhraseTemplateForm(forms.ModelForm):
    """汎用文言テンプレートフォーム"""
    
    class Meta:
        model = PhraseTemplate
        fields = ['title', 'content', 'is_active', 'display_order']
        widgets = {
            'title': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'content': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        selected_title = kwargs.pop('selected_title', None)
        super().__init__(*args, **kwargs)
        
        # 全てのフィールドを必須にする（is_activeは除く）
        for field_name, field in self.fields.items():
            if field_name != 'is_active':
                field.required = True
        
        # 表示順のデフォルト値を設定
        if not self.instance.pk:
            self.fields['display_order'].initial = 0
        
        # 選択されたタイトルがある場合の処理
        if selected_title:
            # タイトルフィールドを非表示にして、hiddenフィールドに変更
            self.fields['title'].widget = forms.HiddenInput()
            self.fields['title'].initial = selected_title
            
            # タイトルの書式に基づいてcontentフィールドのウィジェットを設定
            if selected_title.format_type == 'textarea':
                self.fields['content'].widget = forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4})
        else:
            # タイトルの選択肢を有効なもののみに限定
            from .models_phrase import PhraseTemplateTitle
            self.fields['title'].queryset = PhraseTemplateTitle.get_active_list()
            
            # タイトルの書式に基づいてcontentフィールドのウィジェットを動的に変更
            if self.instance and self.instance.pk and self.instance.title:
                if self.instance.title.format_type == 'textarea':
                    self.fields['content'].widget = forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4})
            elif 'title' in self.data:
                # POSTデータからタイトルを取得してウィジェットを設定
                try:
                    title_id = int(self.data['title'])
                    title = PhraseTemplateTitle.objects.get(pk=title_id)
                    if title.format_type == 'textarea':
                        self.fields['content'].widget = forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4})
                except (ValueError, PhraseTemplateTitle.DoesNotExist):
                    pass