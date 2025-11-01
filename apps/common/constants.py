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


# 使用例
"""
使用例:

定数での比較:
    from apps.common.constants import Constants
    
    # 従来: if contract.status == '10':
    # 新方式:
    if contract.status == Constants.CONTRACT_STATUS.APPROVED:
        print("契約が承認されました")
    
    # 汎用文言テンプレートタイトルキーの使用:
    if title_key == Constants.PHRASE_TEMPLATE_TITLE.HAKEN_RESPONSIBILITY_DEGREE:
        print("派遣・責任の程度")
        
    # 必要に応じて他の定数も追加
"""