import re
from django import forms
import unicodedata

def to_fullwidth_katakana(text):
    # ひらがな→カタカナ
    text = re.sub(r'[ぁ-ん]', lambda m: chr(ord(m.group(0)) + 0x60), text)
    # 半角カタカナ→全角カタカナ
    text = unicodedata.normalize('NFKC', text)
    return text

def validate_kana(value):
    # カタカナ（全角・半角）を許可
    # 全角カタカナ: \u30A0-\u30FF, 半角カナ: \uFF65-\uFF9F, 長音: ー
    if not re.fullmatch(r'[\u30A0-\u30FF\uFF65-\uFF9Fー\uFF9E\uFF9F\u3099\u309A]+', value):
        raise forms.ValidationError('カナはカタカナ（全角・半角）で入力してください。')
