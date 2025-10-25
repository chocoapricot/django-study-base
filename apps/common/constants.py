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
        PENDING = '5'    # 申請中
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

    # 責任の程度 (haken_responsibility_degree)
    class HAKEN_RESPONSIBILITY_DEGREE:
        NO_POSITION = '3'           # 役職なし
        VICE_LEADER = '4'           # 副リーダー（部下２名、リーダー不在の間における緊急対応が週１回程度有）
        NO_POSITION_NO_AUTH = '5'   # 役職無し、付与される権限無し


# 使用例
"""
使用例:

定数での比較:
    from apps.common.constants import Constants
    
    # 従来: if contract.status == '10':
    # 新方式:
    if contract.status == Constants.CONTRACT_STATUS.APPROVED:
        print("契約が承認されました")
    
    # 責任の程度の比較:
    if responsibility_degree == Constants.HAKEN_RESPONSIBILITY_DEGREE.NO_POSITION:
        print("役職なし")
        
    # 必要に応じて他の定数も追加
"""