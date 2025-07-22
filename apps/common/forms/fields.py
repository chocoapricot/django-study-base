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
    # カタカナ・ひらがなのみ許可
    if not re.fullmatch(r'[\u30A0-\u30FF\u3040-\u309Fー\uFF9E\uFF9F\u3099\u309A]+', value):
        raise forms.ValidationError('カナはカタカナまたはひらがなのみ入力してください。')
