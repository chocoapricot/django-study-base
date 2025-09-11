from django.test import TestCase
from apps.connect.templatetags.connect_tags import get_item, diff_class

class ConnectTagsTest(TestCase):

    def test_get_item_filter(self):
        """
        get_item フィルタが辞書から正しく値を取得できることをテスト
        """
        my_dict = {'name': 'Taro', 'age': 30}
        self.assertEqual(get_item(my_dict, 'name'), 'Taro')
        self.assertEqual(get_item(my_dict, 'age'), 30)
        self.assertIsNone(get_item(my_dict, 'city'))

    def test_diff_class_same_values(self):
        """
        diff_class タグが同じ値のペアに対して空文字列を返すことをテスト
        """
        self.assertEqual(diff_class('a', 'a'), '')
        self.assertEqual(diff_class(123, '123'), '')
        self.assertEqual(diff_class(None, ''), '')
        self.assertEqual(diff_class('', None), '')
        self.assertEqual(diff_class('  test  ', 'test'), '')
        self.assertEqual(diff_class(0, '0'), '')

    def test_diff_class_different_values(self):
        """
        diff_class タグが異なる値のペアに対してデフォルトのクラス名を返すことをテスト
        """
        self.assertEqual(diff_class('a', 'b'), 'table-warning')
        self.assertEqual(diff_class('a', None), 'table-warning')
        self.assertEqual(diff_class(1, 2), 'table-warning')
        self.assertEqual(diff_class(0, ''), 'table-warning')

    def test_diff_class_custom_class_name(self):
        """
        diff_class タグが異なる値のペアに対してカスタムクラス名を返すことをテスト
        """
        self.assertEqual(diff_class('a', 'b', class_name='highlight'), 'highlight')
