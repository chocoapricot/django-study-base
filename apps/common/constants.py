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

    # スタッフ登録区分（staff_regist_status）
    class STAFF_REGIST_STATUS:
        REGISTERING = '1'   # 登録中
        REVIEWING = '2'     # 審査中
        TEMPORARY = '10'    # 仮登録
        REGISTERED = '20'   # 登録済
        REJECTED = '90'     # 登録不可

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

    # 限定の別 (limit_by_agreement)
    class LIMIT_BY_AGREEMENT:
        NOT_LIMITED = '0' # 限定しない
        LIMITED = '1'     # 限定する


# 使用例
"""
使用例:

定数での比較:
    from apps.common.constants import Constants

    # 従来: if contract.status == '10':
    # 新方式:
    if contract.status == Constants.CONTRACT_STATUS.APPROVED:
        print("契約が承認されました")

    # 必要に応じて他の定数も追加
"""