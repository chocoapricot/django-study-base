# -*- coding: utf-8 -*-
"""
アプリケーション全体で使用する定数を一元管理するモジュール

Dropdownsテーブルの値を定数として使用し、ハードコードされた値との比較を避ける
"""


class Constants:
    """
    静的定数クラス
    Dropdownsテーブルの実際の値を定数として定義
    """
    
    # 契約ステータス（contract_status）
    class CONTRACT_STATUS:
        DRAFT = '1'      # 作成中
        PENDING = '5'    # 申請
        APPROVED = '10'  # 承認済
        ISSUED = '20'    # 発行済
        CONFIRMED = '30' # 契約済
    
    # 性別（sex）
    class SEX:
        MALE = '1'    # 男性
        FEMALE = '2'  # 女性

    # 契約書パターン ドメイン (domain)
    class DOMAIN:
        STAFF = '1'    # スタッフ
        CLIENT = '10'  # クライアント

    # 契約種別 (client_contract_type)
    class CLIENT_CONTRACT_TYPE:
        CONTRACT = '1'   # 請負
        QUASI_MANDATE = '10' # 準委任
        DISPATCH = '20' # 派遣

    # 支払単位 (pay_unit)
    class PAY_UNIT:
        HOURLY = '10' # 時間給
        DAILY = '20'  # 日給
        MONTHLY = '30' # 月給

    # 請求単位 (bill_unit)
    class BILL_UNIT:
        HOURLY_RATE = '10' # 時間単価
        DAILY_RATE = '20'  # 日額
        MONTHLY_RATE = '30' # 月額

    # 限定の別 (limit_by_agreement)
    class LIMIT_BY_AGREEMENT:
        NOT_LIMITED = '0' # 限定しない
        LIMITED = '1'     # 限定する

    # 汎用文言テンプレートタイトルキー
    class PHRASE_TEMPLATE_TITLE:
        STAFF_NO_HEALTH_INSURANCE = 'STAFF_NO_HEALTH_INSURANCE'      # 健康保険非加入理由
        STAFF_NO_PENSION_INSURANCE = 'STAFF_NO_PENSION_INSURANCE'    # 厚生年金非加入理由
        STAFF_NO_EMPLOYMENT_INSURANCE = 'STAFF_NO_EMPLOYMENT_INSURANCE'  # 雇用保険非加入理由
        HAKEN_TEISHOKUBI_EXEMPT = 'HAKEN_TEISHOKUBI_EXEMPT'          # 派遣抵触日制限外
        HAKEN_RESPONSIBILITY_DEGREE = 'HAKEN_RESPONSIBILITY_DEGREE'  # 派遣・責任の程度
        CONTRACT_BUSINESS_CONTENT = 'CONTRACT_BUSINESS_CONTENT'      # 業務内容
        HAKEN_DIRECT_EMPLOYMENT = 'ANTEI_EMPLOYMENT_REQUEST'         # 派遣先への直接雇用の依頼
        HAKEN_NEW_DISPATCH = 'ANTEI_NEW_HAKEN_OFFER'                 # 新たな派遣先の提供
        HAKEN_INDEFINITE_EMPLOYMENT = 'ANTEI_MUKI_EMPLOYMENT'        # 派遣元での無期雇用化
        HAKEN_OTHER_MEASURES = 'ANTEI_OTHERS'                        # その他の雇用安定措置

    # 契約割り当て確認種別 (assignment_confirm_type)
    class ASSIGNMENT_CONFIRM_TYPE:
        EXTEND = '10'     # 延長予定
        TERMINATE = '90'  # 終了予定

    # メール種別 (mail_type)
    class MAIL_TYPE:
        SIGNUP = 'signup'                   # サインアップ確認
        PASSWORD_RESET = 'password_reset'   # パスワードリセット
        PASSWORD_CHANGE = 'password_change' # パスワード変更通知
        GENERAL = 'general'                 # 一般

    # メール送信ステータス (mail_status)
    class MAIL_STATUS:
        SENT = 'sent'       # 送信成功
        FAILED = 'failed'   # 送信失敗
        PENDING = 'pending' # 送信待ち

    # アプリケーション操作 (app_action)
    class APP_ACTION:
        CREATE = 'create'           # 作成
        UPDATE = 'update'           # 編集
        DELETE = 'delete'           # 削除
        LOGIN = 'login'             # ログイン
        LOGIN_FAILED = 'login_failed' # ログイン失敗
        LOGOUT = 'logout'           # ログアウト
        VIEW = 'view'               # 閲覧
        PRINT = 'print'             # 印刷

    # 接続ステータス (connect_status)
    class CONNECT_STATUS:
        PENDING = 'pending'   # 未承認
        APPROVED = 'approved' # 承認済み

    # リクエストステータス (request_status) - 却下を含む
    class REQUEST_STATUS:
        PENDING = 'pending'   # 未承認
        APPROVED = 'approved' # 承認済み
        REJECTED = 'rejected' # 却下

    # 派遣待遇決定方式 (dispatch_treatment_method)
    class DISPATCH_TREATMENT_METHOD:
        AGREEMENT = 'agreement'         # 労使協定方式
        EQUAL_BALANCE = 'equal_balance' # 派遣先均等・均衡方式

    # 銀行マスタレコード種別 (bank_record_type)
    class BANK_RECORD_TYPE:
        BANK = '1'   # 銀行
        BRANCH = '2' # 支店

    # 通知種別 (notification_type)
    class NOTIFICATION_TYPE:
        GENERAL = 'general'  # 一般
        ALERT = 'alert'      # アラート
        INFO = 'info'        # 情報
        WARNING = 'warning'  # 警告

    # 時間丸め単位 (time_rounding_unit)
    class TIME_ROUNDING_UNIT:
        ONE_MINUTE = 1      # 1分
        FIVE_MINUTES = 5    # 5分
        TEN_MINUTES = 10    # 10分
        FIFTEEN_MINUTES = 15 # 15分
        THIRTY_MINUTES = 30  # 30分

    # 時間丸め方法 (time_rounding_method)
    class TIME_ROUNDING_METHOD:
        ROUND = 'round'  # 四捨五入
        FLOOR = 'floor'  # 切り捨て
        CEIL = 'ceil'    # 切り上げ

    # 打刻方法 (punch_method)
    class PUNCH_METHOD:
        PUNCH = 'punch'             # 打刻
        E_STAFFING = 'e-staffing'   # e-staffing
        HRMOS = 'hrmos'             # HRMOS
        KING_OF_TIME = 'kot'        # KING OF TIME
        TOUCH_ON_TIME = 'tot'       # Touch On Time
        MANUAL = 'manual'           # 手入力

    # 勤怠ステータス (kintai_status)
    class KINTAI_STATUS:
        DRAFT = '10'      # 作成中
        SUBMITTED = '20'  # 提出済み
        APPROVED = '30'   # 承認済み
        REJECTED = '40'   # 差戻し

    # 勤務区分 (work_type)
    class WORK_TYPE:
        WORK = '10'       # 出勤
        HOLIDAY = '20'    # 休日
        ABSENCE = '30'    # 欠勤
        PAID_LEAVE = '40' # 有給休暇
        SPECIAL_LEAVE = '50' # 特別休暇
        COMPENSATORY_LEAVE = '60' # 代休
        NO_WORK = '70'    # 稼働無し

    # 時間外算出方式 (calculation_type)
    class OVERTIME_CALCULATION_TYPE:
        PREMIUM = 'premium'             # 割増
        MONTHLY_RANGE = 'monthly_range' # 月単位時間範囲
        VARIABLE = 'variable'           # 1ヶ月単位変形労働
        FLEXTIME = 'flextime'           # 1ヶ月単位フレックス

    # データ形式 (format_type)
    class FORMAT_TYPE:
        TEXT = 'text'
        TEXTAREA = 'textarea'
        BOOLEAN = 'boolean'
        NUMBER = 'number'
        CHOICE = 'choice'
        COLOR = 'color'

    # マスタ階層レベル (master_level)
    class MASTER_LEVEL:
        CATEGORY = 1
        ITEM = 2

    # 契約文言表示場所 (display_position)
    class CONTRACT_TERM_POSITION:
        PREAMBLE = 1    # 前文
        BODY = 2        # 本文
        POSTSCRIPT = 3  # 末文

    # 評価点 (evaluation_rating)
    class EVALUATION_RATING:
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5

    # 印刷種別 (print_type)
    class PRINT_TYPE:
        CONTRACT = '10'                 # 契約書
        QUOTATION = '20'                # 見積書
        TEISHOKUBI_NOTIFICATION = '30'  # 抵触日通知書
        DISPATCH_NOTIFICATION = '40'    # 派遣先通知書
        DISPATCH_LEDGER = '50'          # 派遣先管理台帳
        EMPLOYMENT_CONDITIONS = '10'    # 就業条件明示書 (契約アサイン)


# CHOICESリスト生成ヘルパー(モデルで使用)
def get_mail_type_choices():
    """メール種別の選択肢リストを返す"""
    return [
        (Constants.MAIL_TYPE.SIGNUP, 'サインアップ確認'),
        (Constants.MAIL_TYPE.PASSWORD_RESET, 'パスワードリセット'),
        (Constants.MAIL_TYPE.PASSWORD_CHANGE, 'パスワード変更通知'),
        (Constants.MAIL_TYPE.GENERAL, '一般'),
    ]

def get_mail_status_choices():
    """メール送信ステータスの選択肢リストを返す"""
    return [
        (Constants.MAIL_STATUS.SENT, '送信成功'),
        (Constants.MAIL_STATUS.FAILED, '送信失敗'),
        (Constants.MAIL_STATUS.PENDING, '送信待ち'),
    ]

def get_app_action_choices():
    """アプリケーション操作の選択肢リストを返す"""
    return [
        (Constants.APP_ACTION.CREATE, '作成'),
        (Constants.APP_ACTION.UPDATE, '編集'),
        (Constants.APP_ACTION.DELETE, '削除'),
        (Constants.APP_ACTION.LOGIN, 'ログイン'),
        (Constants.APP_ACTION.LOGIN_FAILED, 'ログイン失敗'),
        (Constants.APP_ACTION.LOGOUT, 'ログアウト'),
        (Constants.APP_ACTION.VIEW, '閲覧'),
        (Constants.APP_ACTION.PRINT, '印刷'),
    ]

def get_connect_status_choices():
    """接続ステータスの選択肢リストを返す"""
    return [
        (Constants.CONNECT_STATUS.PENDING, '未承認'),
        (Constants.CONNECT_STATUS.APPROVED, '承認済み'),
    ]

def get_request_status_choices():
    """リクエストステータスの選択肢リストを返す（却下を含む）"""
    return [
        (Constants.REQUEST_STATUS.PENDING, '未承認'),
        (Constants.REQUEST_STATUS.APPROVED, '承認済み'),
        (Constants.REQUEST_STATUS.REJECTED, '却下'),
    ]

def get_dispatch_treatment_method_choices():
    """派遣待遇決定方式の選択肢リストを返す"""
    return [
        (Constants.DISPATCH_TREATMENT_METHOD.AGREEMENT, '労使協定方式'),
        (Constants.DISPATCH_TREATMENT_METHOD.EQUAL_BALANCE, '派遣先均等・均衡方式'),
    ]

def get_notification_type_choices():
    """通知種別の選択肢リストを返す"""
    return [
        (Constants.NOTIFICATION_TYPE.GENERAL, '一般'),
        (Constants.NOTIFICATION_TYPE.ALERT, 'アラート'),
        (Constants.NOTIFICATION_TYPE.INFO, '情報'),
        (Constants.NOTIFICATION_TYPE.WARNING, '警告'),
    ]


def get_pay_unit_choices():
    """支払単位の選択肢リストを返す"""
    return [
        (Constants.PAY_UNIT.HOURLY, '時給'),
        (Constants.PAY_UNIT.DAILY, '日給'),
        (Constants.PAY_UNIT.MONTHLY, '月給'),
    ]


def get_time_rounding_unit_choices():
    """時間丸め単位の選択肢リストを返す"""
    return [
        (Constants.TIME_ROUNDING_UNIT.ONE_MINUTE, '1分'),
        (Constants.TIME_ROUNDING_UNIT.FIVE_MINUTES, '5分'),
        (Constants.TIME_ROUNDING_UNIT.TEN_MINUTES, '10分'),
        (Constants.TIME_ROUNDING_UNIT.FIFTEEN_MINUTES, '15分'),
        (Constants.TIME_ROUNDING_UNIT.THIRTY_MINUTES, '30分'),
    ]


def get_time_rounding_method_choices():
    """時間丸め方法の選択肢リストを返す"""
    return [
        (Constants.TIME_ROUNDING_METHOD.ROUND, '四捨五入'),
        (Constants.TIME_ROUNDING_METHOD.FLOOR, '切り捨て'),
        (Constants.TIME_ROUNDING_METHOD.CEIL, '切り上げ'),
    ]


def get_punch_method_choices():
    """打刻方法の選択肢リストを返す"""
    return [
        (Constants.PUNCH_METHOD.PUNCH, '打刻'),
        (Constants.PUNCH_METHOD.E_STAFFING, 'e-staffing'),
        (Constants.PUNCH_METHOD.HRMOS, 'HRMOS'),
        (Constants.PUNCH_METHOD.KING_OF_TIME, 'KING OF TIME'),
        (Constants.PUNCH_METHOD.TOUCH_ON_TIME, 'Touch On Time'),
        (Constants.PUNCH_METHOD.MANUAL, '手入力'),
    ]


def get_domain_choices():
    """ドメインの選択肢リストを返す"""
    return [
        (Constants.DOMAIN.STAFF, 'スタッフ'),
        (Constants.DOMAIN.CLIENT, 'クライアント'),
    ]


def get_kintai_status_choices():
    """勤怠ステータスの選択肢リストを返す"""
    return [
        (Constants.KINTAI_STATUS.DRAFT, '作成中'),
        (Constants.KINTAI_STATUS.SUBMITTED, '提出済み'),
        (Constants.KINTAI_STATUS.APPROVED, '承認済み'),
        (Constants.KINTAI_STATUS.REJECTED, '差戻し'),
    ]


def get_staff_work_type_choices():
    """スタッフ勤務区分の選択肢リストを返す"""
    return [
        (Constants.WORK_TYPE.WORK, '出勤'),
        (Constants.WORK_TYPE.HOLIDAY, '休日'),
        (Constants.WORK_TYPE.ABSENCE, '欠勤'),
        (Constants.WORK_TYPE.PAID_LEAVE, '有給休暇'),
        (Constants.WORK_TYPE.SPECIAL_LEAVE, '特別休暇'),
        (Constants.WORK_TYPE.COMPENSATORY_LEAVE, '代休'),
        (Constants.WORK_TYPE.NO_WORK, '稼働無し'),
    ]


def get_client_work_type_choices():
    """クライアント勤務区分の選択肢リストを返す"""
    return [
        (Constants.WORK_TYPE.WORK, '出勤'),
        (Constants.WORK_TYPE.HOLIDAY, '休日'),
        (Constants.WORK_TYPE.ABSENCE, '欠勤'),
        (Constants.WORK_TYPE.NO_WORK, '稼働無し'),
    ]


def get_overtime_calculation_type_choices():
    """時間外算出方式の選択肢リストを返す"""
    return [
        (Constants.OVERTIME_CALCULATION_TYPE.PREMIUM, '割増'),
        (Constants.OVERTIME_CALCULATION_TYPE.MONTHLY_RANGE, '月単位時間範囲'),
        (Constants.OVERTIME_CALCULATION_TYPE.VARIABLE, '1ヶ月単位変形労働'),
        (Constants.OVERTIME_CALCULATION_TYPE.FLEXTIME, '1ヶ月単位フレックス'),
    ]


def get_default_value_format_choices():
    """初期値マスタ形式の選択肢リストを返す"""
    return [
        (Constants.FORMAT_TYPE.TEXT, 'テキスト'),
        (Constants.FORMAT_TYPE.TEXTAREA, 'テキストエリア'),
        (Constants.FORMAT_TYPE.BOOLEAN, '真偽値'),
        (Constants.FORMAT_TYPE.NUMBER, '数値'),
    ]


def get_generative_ai_setting_format_choices():
    """生成AI設定形式の選択肢リストを返す"""
    return [
        (Constants.FORMAT_TYPE.TEXT, 'テキスト'),
        (Constants.FORMAT_TYPE.TEXTAREA, 'テキストエリア'),
        (Constants.FORMAT_TYPE.BOOLEAN, '真偽値'),
        (Constants.FORMAT_TYPE.NUMBER, '数値'),
        (Constants.FORMAT_TYPE.CHOICE, '選択肢'),
    ]


def get_user_parameter_format_choices():
    """ユーザーパラメータ形式の選択肢リストを返す"""
    return [
        (Constants.FORMAT_TYPE.TEXT, 'テキスト'),
        (Constants.FORMAT_TYPE.TEXTAREA, 'テキストエリア'),
        (Constants.FORMAT_TYPE.BOOLEAN, '真偽値'),
        (Constants.FORMAT_TYPE.NUMBER, '数値'),
        (Constants.FORMAT_TYPE.CHOICE, '選択肢'),
        (Constants.FORMAT_TYPE.COLOR, '色'),
    ]


def get_phrase_template_format_choices():
    """汎用文言テンプレート書式の選択肢リストを返す"""
    return [
        (Constants.FORMAT_TYPE.TEXT, 'テキスト'),
        (Constants.FORMAT_TYPE.TEXTAREA, 'テキストエリア'),
    ]


def get_qualification_level_choices():
    """資格階層レベルの選択肢リストを返す"""
    return [
        (Constants.MASTER_LEVEL.CATEGORY, 'カテゴリ'),
        (Constants.MASTER_LEVEL.ITEM, '資格'),
    ]


def get_skill_level_choices():
    """技能階層レベルの選択肢リストを返す"""
    return [
        (Constants.MASTER_LEVEL.CATEGORY, 'カテゴリ'),
        (Constants.MASTER_LEVEL.ITEM, '技能'),
    ]


def get_contract_term_position_choices():
    """契約文言表示場所の選択肢リストを返す"""
    return [
        (Constants.CONTRACT_TERM_POSITION.PREAMBLE, '前文'),
        (Constants.CONTRACT_TERM_POSITION.BODY, '本文'),
        (Constants.CONTRACT_TERM_POSITION.POSTSCRIPT, '末文'),
    ]


def get_evaluation_rating_choices():
    """評価点の選択肢リストを返す"""
    return [(i, str(i)) for i in range(1, 6)]


def get_client_print_type_choices():
    """クライアント印刷種別の選択肢リストを返す"""
    return [
        (Constants.PRINT_TYPE.CONTRACT, '契約書'),
        (Constants.PRINT_TYPE.QUOTATION, '見積書'),
        (Constants.PRINT_TYPE.TEISHOKUBI_NOTIFICATION, '抵触日通知書'),
        (Constants.PRINT_TYPE.DISPATCH_NOTIFICATION, '派遣先通知書'),
        (Constants.PRINT_TYPE.DISPATCH_LEDGER, '派遣先管理台帳'),
    ]


def get_assignment_print_type_choices():
    """契約アサイン印刷種別の選択肢リストを返す"""
    return [
        (Constants.PRINT_TYPE.EMPLOYMENT_CONDITIONS, '就業条件明示書'),
    ]


def get_limit_by_agreement_choices():
    """限定の別の選択肢リストを返す"""
    return [
        (Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED, '限定しない'),
        (Constants.LIMIT_BY_AGREEMENT.LIMITED, '限定する')
    ]


def get_assignment_confirm_type_choices():
    """契約割り当て確認種別の選択肢リストを返す"""
    return [
        (Constants.ASSIGNMENT_CONFIRM_TYPE.EXTEND, '延長予定'),
        (Constants.ASSIGNMENT_CONFIRM_TYPE.TERMINATE, '終了予定')
    ]


def get_break_input_choices():
    """休憩入力の選択肢リストを返す"""
    return [
        (True, '入力する'),
        (False, '入力しない'),
    ]


def get_location_fetch_choices():
    """位置情報取得の選択肢リストを返す"""
    return [
        (True, '取得する'),
        (False, '取得しない'),
    ]


# 使用例
"""
使用例:

定数での比較:
    from apps.common.constants import Constants
    
    # 契約ステータス
    if contract.status == Constants.CONTRACT_STATUS.APPROVED:
        print("契約が承認されました")
    
    # メールステータス
    if mail_log.status == Constants.MAIL_STATUS.SENT:
        print("メール送信成功")
    
    # 接続ステータス
    if connect.status == Constants.CONNECT_STATUS.APPROVED:
        print("接続が承認されました")
    
    # 銀行レコード種別
    if record_type == Constants.BANK_RECORD_TYPE.BANK:
        print("銀行レコード")
    
    # 時間丸め設定
    if time_rounding.start_time_unit == Constants.TIME_ROUNDING_UNIT.FIFTEEN_MINUTES:
        print("15分単位で丸め")
    
    if time_rounding.start_time_method == Constants.TIME_ROUNDING_METHOD.ROUND:
        print("四捨五入で処理")

モデルでの使用:
    from apps.common.constants import (
        Constants,
        get_mail_type_choices,
        get_time_rounding_unit_choices,
        get_time_rounding_method_choices,
        get_break_input_choices
    )
    
    mail_type = models.CharField(
        'メール種別',
        max_length=20,
        choices=get_mail_type_choices(),
        default=Constants.MAIL_TYPE.GENERAL
    )
    
    start_time_unit = models.IntegerField(
        choices=get_time_rounding_unit_choices(),
        default=Constants.TIME_ROUNDING_UNIT.FIFTEEN_MINUTES,
        verbose_name='開始時刻丸め単位'
    )
    
    start_time_method = models.CharField(
        max_length=10,
        choices=get_time_rounding_method_choices(),
        default=Constants.TIME_ROUNDING_METHOD.ROUND,
        verbose_name='開始時刻端数処理'
    )
"""