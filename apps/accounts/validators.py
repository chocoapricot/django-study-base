import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from apps.system.settings.utils import my_parameter


class MyPasswordValidator:
    """
    パスワードに記号（特殊文字）が1つ以上含まれていること・最小文字数をパラメータから取得して判定するバリデータ
    """
    def validate(self, password, user=None):
        # パラメータから取得
        symbol_required = my_parameter('PASSWORD_SYMBOL_REQUIRED', 'true')  # 'true'なら必須
        min_length = int(my_parameter('PASSWORD_MIN_LENGTH', '8'))
        max_length_param = my_parameter('PASSWORD_MAX_LENGTH', None)
        try:
            max_length = int(max_length_param)
            if max_length <= 0:
                max_length = None
        except (TypeError, ValueError):
            max_length = None

        # 最小文字数チェック
        if len(password) < min_length:
            raise ValidationError(
                _(f"パスワードは{min_length}文字以上で入力してください。"),
                code='password_too_short',
            )
        # 最大文字数チェック（設定がある場合のみ）
        #print(f"[DEBUG] max_length={max_length}, len(password)={len(password)}, password='{password}'")
        if max_length is not None and len(password) > max_length:
            #print(f"[DEBUG] パスワード長超過: {len(password)} > {max_length}")
            raise ValidationError(
                _(f"パスワードは{max_length}文字以下で入力してください。"),
                code='password_too_long',
            )

        # 記号必須チェック
        if symbol_required == 'true':
            # 記号の正規表現（シングルクォート・括弧・バックスラッシュを含める）
            if not re.search(r"[!\"@#$%\^&\*\-_=\+\?\(\)\{\}\|\[\]\\:;<>,./']", password):
                raise ValidationError(
                    _("パスワードには少なくとも1つの記号（!@#$%^&* など）が必要です。"),
                    code='password_no_symbol',
                )

    def get_help_text(self):
        symbol_required = my_parameter('PASSWORD_SYMBOL_REQUIRED', 'true')
        min_length = int(my_parameter('PASSWORD_MIN_LENGTH', '8'))
        max_length_param = my_parameter('PASSWORD_MAX_LENGTH', None)
        try:
            max_length = int(max_length_param)
            if max_length <= 0:
                max_length = None
        except (TypeError, ValueError):
            max_length = None
        msg = f"パスワードは{min_length}文字以上"
        if max_length:
            msg += f"{max_length}文字以下"
        if symbol_required == 'true':
            msg += "、かつ少なくとも1つの記号（!@#$%^&* など）を含めてください。"
        else:
            msg += "で入力してください。"
        return _(msg)