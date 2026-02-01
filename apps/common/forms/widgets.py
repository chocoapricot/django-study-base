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


class BadgeRadioSelect(MyRadioSelect):
    """
    ラベルをバッジ形式で表示するラジオボタン
    badge_class_map: {option_value: css_class} のマッピングを指定可能
    """
    def __init__(self, *args, **kwargs):
        self.badge_class_map = kwargs.pop('badge_class_map', {})
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        if self.choices:
            output = []
            for option_value, option_label in self.choices:
                # Noneや空文字（「選択してください」等）はスキップ
                if not option_value and option_value != 0:
                    continue

                option_id = f"{attrs.get('id', name)}_{option_value}" if attrs and attrs.get('id') else f"{name}_{option_value}"
                checked = 'checked' if str(option_value) == str(value) else ''

                badge_class = self.badge_class_map.get(str(option_value), 'bg-secondary')

                radio_html = format_html(
                    '<div class="form-check form-check-inline">'
                    '<input type="radio" class="form-check-input" name="{}" value="{}" id="{}" {}>'
                    '<label class="form-check-label" for="{}">'
                    '<span class="badge {}">{}</span>'
                    '</label>'
                    '</div>',
                    name, option_value, option_id, checked, option_id, badge_class, option_label
                )
                output.append(radio_html)
            return mark_safe(''.join(output))
        return ''


class BadgeCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """
    ラベルをバッジ形式で表示するチェックボックス（複数選択）
    badge_class_map: {option_value: css_class} のマッピングを指定可能
    """
    def __init__(self, *args, **kwargs):
        self.badge_class_map = kwargs.pop('badge_class_map', {})
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        if self.choices:
            output = []
            for option_value, option_label in self.choices:
                if not option_value and option_value != 0:
                    continue

                option_id = f"{attrs.get('id', name)}_{option_value}" if attrs and attrs.get('id') else f"{name}_{option_value}"

                # 選択状態を判定
                checked = ''
                if value:
                    str_value = [str(v) for v in value]
                    if str(option_value) in str_value:
                        checked = 'checked'

                badge_class = self.badge_class_map.get(str(option_value), 'bg-secondary')

                checkbox_html = format_html(
                    '<div class="form-check form-check-inline">'
                    '<input type="checkbox" class="form-check-input" name="{}" value="{}" id="{}" {}>'
                    '<label class="form-check-label" for="{}">'
                    '<span class="badge {}">{}</span>'
                    '</label>'
                    '</div>',
                    name, option_value, option_id, checked, option_id, badge_class, option_label
                )
                output.append(checkbox_html)
            return mark_safe(''.join(output))
        return ''


class ColorInput(forms.TextInput):
    """
    HTML5の <input type="color"> をレンダリングするためのウィジェット。
    """
    input_type = 'color'
