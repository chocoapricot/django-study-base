from django import forms
from django.forms.widgets import RadioSelect
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class MyRadioSelect(RadioSelect):
    """
    ラジオボタンを横並びで表示するカスタムウィジェット
    Bootstrap の form-check-inline クラスを使用して横並びレイアウトを実現
    """
    
    def render(self, name, value, attrs=None, renderer=None):
        """ラジオボタンを横並びで描画"""
        if self.choices:
            # 各選択肢を横並びで表示
            output = []
            for option_value, option_label in self.choices:
                # ラジオボタンのIDを生成
                option_id = f"{attrs.get('id', name)}_{option_value}" if attrs and attrs.get('id') else f"{name}_{option_value}"
                
                # チェック状態を判定
                checked = 'checked' if str(option_value) == str(value) else ''
                
                # form-check-inline でラップしたラジオボタンを生成
                radio_html = format_html(
                    '<div class="form-check form-check-inline">'
                    '<input type="radio" class="form-check-input" name="{}" value="{}" id="{}" {}>'
                    '<label class="form-check-label" for="{}">{}</label>'
                    '</div>',
                    name, option_value, option_id, checked, option_id, option_label
                )
                output.append(radio_html)
            
            return mark_safe(''.join(output))
        return ''


