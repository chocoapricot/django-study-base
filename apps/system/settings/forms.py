from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html
import re
from .models import Menu

class ColorPickerWidget(forms.TextInput):
    """
    アイコンスタイル（CSS）の中から color:#XXXXXX; を抽出し、
    HTMLのカラーピッカーで選択できるようにするウィジェット。
    """
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
            
        # 元のテキスト入力（icon_style全体を保持）
        final_attrs = self.build_attrs(attrs, {'type': 'text'})
        text_input = super().render(name, value, final_attrs, renderer)
        
        # color:#XXXXXX; の形式を抽出。見つからない場合は黒をデフォルトに。
        color_value = "#000000"
        if value:
            match = re.search(r'color:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})', str(value))
            if match:
                color_value = match.group(1)
        
        # カラーピッカーを追加。変更時にテキスト入力の値を 'color:#XXXXXX;' に更新する。
        # attrs が None の場合を考慮して name を代用
        input_id = final_attrs.get('id', name)
        picker_id = f"{input_id}_picker"
        
        color_input = format_html(
            '<input type="color" id="{}" value="{}" '
            'onchange="document.getElementById(\'{}\').value=\'color:\' + this.value + \';\'" '
            'style="margin-left: 10px; width: 40px; height: 30px; padding: 0; border: 1px solid #ccc; cursor: pointer; vertical-align: middle;">',
            picker_id, color_value, input_id
        )
        
        return mark_safe(f'<div style="display: flex; align-items: center;">{text_input}{color_input}</div>')

class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        exclude = ['version', 'created_at', 'created_by', 'updated_at', 'updated_by']
        widgets = {
            'icon_style': ColorPickerWidget(),
        }
