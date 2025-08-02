from django.core.exceptions import ValidationError
from stdnum.jp import cn as houjin

def validate_corporate_number(value):
    """
    法人番号をstdnumライブラリを使って検証する。
    空の値は許容する。
    """
    if not value:
        return
    
    try:
        houjin.validate(value)
    except Exception as e:
        # stdnum が返す可能性のある様々な例外をまとめて捕捉する
        raise ValidationError(f'法人番号が正しくありません: {e}')