from django.test import TestCase
from django.template import Context, Template

class HelpTagsTemplateTagTest(TestCase):
    """ヘルプタグテンプレートタグのテスト"""

    def test_my_help_icon(self):
        """my_help_iconタグのレンダリングテスト"""
        template = Template('{% load help_tags %}{% my_help_icon "テストヘルプ" %}')
        rendered = template.render(Context({}))

        self.assertIn('data-bs-toggle="tooltip"', rendered)
        self.assertIn('data-bs-trigger="hover focus"', rendered)
        self.assertIn('title="テストヘルプ"', rendered)
        self.assertNotIn('click', rendered)

    def test_my_help_preset(self):
        """my_help_presetタグのレンダリングテスト"""
        # HELP_TEXTSにあるキーを使用
        template = Template('{% load help_tags %}{% my_help_preset "corporate_number" %}')
        rendered = template.render(Context({}))

        self.assertIn('data-bs-toggle="tooltip"', rendered)
        self.assertIn('data-bs-trigger="hover focus"', rendered)
        self.assertIn('title="半角数字13桁ハイフンなし"', rendered)
        self.assertNotIn('click', rendered)

    def test_my_note_icon(self):
        """my_note_iconタグのレンダリングテスト"""
        template = Template('{% load help_tags %}{% my_note_icon "テスト補足" %}')
        rendered = template.render(Context({}))

        self.assertIn('bi-book', rendered)
        self.assertIn('data-bs-toggle="tooltip"', rendered)
        self.assertIn('data-bs-trigger="hover focus"', rendered)
        self.assertIn('title="テスト補足"', rendered)
        self.assertNotIn('click', rendered)

    def test_my_note_preset(self):
        """my_note_presetタグのレンダリングテスト"""
        template = Template('{% load help_tags %}{% my_note_preset "unknown_key" %}')
        rendered = template.render(Context({}))

        self.assertIn('bi-book', rendered)
        self.assertIn('data-bs-toggle="tooltip"', rendered)
        self.assertIn('data-bs-trigger="hover focus"', rendered)
        self.assertIn('title="unknown_key"', rendered)
        self.assertNotIn('click', rendered)
