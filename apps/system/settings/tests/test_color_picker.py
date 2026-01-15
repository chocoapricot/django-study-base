from django.test import TestCase
from apps.system.settings.forms import MenuForm, ColorPickerWidget
from apps.system.settings.models import Menu

class ColorPickerWidgetTest(TestCase):
    def test_widget_extraction(self):
        """ウィジェットがCSSから色を正しく抽出できるかテスト"""
        widget = ColorPickerWidget()
        
        # 色が含まれる場合
        html = widget.render('test', 'color:#ff0000; font-size:12px;')
        self.assertIn('value="#ff0000"', html)
        
        # 色が含まれない場合（デフォルト）
        html = widget.render('test', 'font-size:12px;')
        self.assertIn('value="#000000"', html)

class MenuFormTest(TestCase):
    def test_form_valid_with_style(self):
        """フォームが有効かテスト"""
        form_data = {
            'name': 'Test Menu',
            'url': '/',
            'icon': 'bi-house',
            'icon_style': 'color:#00ff00;',
            'level': 0,
            'disp_seq': 1,
            'active': True
        }
        form = MenuForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['icon_style'], 'color:#00ff00;')
