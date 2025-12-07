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

モデルでの使用:
    from apps.common.constants import get_mail_type_choices
    
    mail_type = models.CharField(
        'メール種別',
        max_length=20,
        choices=get_mail_type_choices(),
        default=Constants.MAIL_TYPE.GENERAL
    )
"""