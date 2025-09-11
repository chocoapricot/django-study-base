from django.test import TestCase
from apps.connect.templatetags.connect_tags import get_item

class ConnectTagsTest(TestCase):

    def test_get_item_filter(self):
        """
        get_item フィルタが辞書から正しく値を取得できることをテスト
        """
        my_dict = {'name': 'Taro', 'age': 30}
        self.assertEqual(get_item(my_dict, 'name'), 'Taro')
        self.assertEqual(get_item(my_dict, 'age'), 30)
        self.assertIsNone(get_item(my_dict, 'city'))
