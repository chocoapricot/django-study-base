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