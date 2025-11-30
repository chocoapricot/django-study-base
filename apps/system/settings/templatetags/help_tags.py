"""
ヘルプアイコン用テンプレートタグ
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def my_help_icon(text, placement='top'):
    """
    ヘルプアイコンを表示するテンプレートタグ
    
    使用例:
    {% load help_tags %}
    {% my_help_icon "社員番号・入社日が登録されているスタッフのみ選択可能" %}
    {% my_help_icon "半角数字13桁ハイフンなし" "right" %}
    """
    html = f'''<i class="bi bi-question-circle" style="color: #66bbff; cursor: pointer;" 
               data-bs-toggle="tooltip" data-bs-placement="{placement}" 
               title="{text}"></i>'''
    return mark_safe(html)


# よく使用されるヘルプテキストの定数
HELP_TEXTS = {
    # 電話番号
    'phone': '電話番号は数字とハイフンのみ入力してください',
    'phone_number': '電話番号は数字とハイフンのみ入力してください',
    # 基本入力フォーマット
    'corporate_number': '半角数字13桁ハイフンなし',
    'postal_code': '半角数字7桁ハイフンなし',
    
    # API関連
    'gbiz_api': '経産省のgBizINFO-APIで取得',
    'postal_api': 'フリーの郵便番号APIで取得',
    
    # スタッフ関連
    'hire_date': '入社日登録しないと契約登録不可',
    'resignation_date': '契約期間終了日は退職日まで',
    'employee_no': '半角英数字10文字まで（空欄可）、社員番号登録しないと契約登録不可',
    'department_code': '現在有効な部署のみ表示',
    'staff_selection': '社員番号・入社日が登録されているスタッフのみ選択可能',
    
    # クライアント関連
    'client_selection': '基本契約が締結され、法人番号が登録されているクライアントのみ選択可能です。',
    'basic_contract_date': '個別契約開始日は基本契約締結日以降',
    
    # 契約関連
    'contract_start_date_client': '基本契約締結日以降である必要あり',
    'contract_start_date_staff': '契約期間は入社日～退職日内の必要あり',
    'worktime_pattern_staff': 'スタッフの雇用形態で就業時間が設定されている場合は自動設定され変更不可',
    'overtime_pattern_staff': 'スタッフの雇用形態で時間外算出が設定されている場合は自動設定され変更不可',
    
    # 契約選択関連
    'staff_employee_no': '契約対象となるスタッフには社員番号が必要です',
    'staff_hire_date': '契約開始日は入社日以降である必要があります',
    'client_basic_contract': '契約開始日は基本契約締結日以降である必要があります',
    
    # 勤怠関連
    'daily_overtime_enabled': '1日にこの時間を超えると、残業時間として集計されます。',
    'monthly_overtime_enabled': '1ヶ月の残業時間がこの時間を超えると、割増時間として集計されます。',
    'calculate_midnight_premium': '22時から5時までの勤務時間が、深夜時間として集計されます。',
    'premium_overtime': '1ヶ月の残業時間が特定時間を超える場合',
    'late_night_overtime': '22時から5時までの勤務時間が、深夜時間として集計されます。',
    'monthly_range_premium': '1ヶ月の勤務時間が特定時間を超える場合',
    'monthly_range_deduction': '1ヶ月の勤務時間が特定時間を下回る場合',

    # 銀行・支払い関連
    'bank_code': '4桁の数字で入力（必須）',
    'branch_code': '3桁の数字で入力（必須）',
    'account_number': '1-8桁の数字で入力',
    'closing_day': '月末締めの場合は31を入力',
    'invoice_schedule': '締め日から何か月後の何日まで請求書必着',
    'payment_schedule': '締め日から何か月後の何日払い',
    
    # 会社・部署関連
    'valid_period': '未入力の場合は無期限',
    
    # ファイル関連
    'file_hash': 'PDFファイルのSHA256ハッシュ値（ファイルの完全性確認用）',
}


@register.simple_tag
def my_help_preset(key, placement='top'):
    """
    事前定義されたヘルプテキストを表示するテンプレートタグ
    
    使用例:
    {% my_help_preset "corporate_number" %}
    {% my_help_preset "staff_selection" "right" %}
    """
    text = HELP_TEXTS.get(key, key)
    html = f'''<i class="bi bi-question-circle" style="color: #66bbff; cursor: pointer;" 
               data-bs-toggle="tooltip" data-bs-placement="{placement}" 
               title="{text}"></i>'''
    return mark_safe(html)


@register.simple_tag
def my_note_icon(text, placement='top'):
    """
    補足アイコンを表示するテンプレートタグ
    """
    html = f'''<i class="bi bi-book" style="color: #66bbff; cursor: pointer;"
               data-bs-toggle="tooltip" data-bs-placement="{placement}"
               title="{text}"></i>'''
    return mark_safe(html)


# よく使用される補足テキストの定数
NOTE_TEXTS = {
}


@register.simple_tag
def my_note_preset(key, placement='top'):
    """
    事前定義された補足テキストを表示するテンプレートタグ
    """
    text = NOTE_TEXTS.get(key, key)
    html = f'''<i class="bi bi-book" style="color: #66bbff; cursor: pointer;"
               data-bs-toggle="tooltip" data-bs-placement="{placement}"
               title="{text}"></i>'''
    return mark_safe(html)


@register.filter
def lookup(choices, key):
    """
    選択肢から値に対応するラベルを取得するフィルター
    
    使用例:
    {{ form.sex.field.choices|lookup:form.sex.value }}
    """
    if not choices or not key:
        return ''
    
    for choice_key, choice_label in choices:
        if str(choice_key) == str(key):
            return choice_label
    return ''