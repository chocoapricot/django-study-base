#!/usr/bin/env python
"""
スタッフ評価のサンプルデータを100件作成するスクリプト。
10件の評価文言を取得し、それぞれに対して10人のスタッフをランダムに選んで評価データを登録。
"""

import os
import sys
import django
import random
from datetime import date, timedelta

# Django設定の読み込み
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.staff.models import Staff, StaffEvaluation
from apps.common.gemini_utils import call_gemini_api
from apps.master.models import GenerativeAiSetting

def get_evaluation_data():
    """
    AIからスタッフ評価の文言と点数を10件取得する。
    """
    prompt = """
    スタッフ評価のコメントと1-5の評価点を10件生成してください。
    各コメントは日本語で、ポジティブな評価内容にしてください。
    必ず有効なJSON形式で返してください。形式: [{"comment": "コメント", "rating": 点数}, ...]
    他のテキストは含めないでください。
    """
    
    result = call_gemini_api(prompt.strip())
    if result.get('success'):
        try:
            text = result['text'].strip()
            # JSON部分を抽出（```json ... ``` で囲まれている場合）
            if text.startswith('```json'):
                text = text[7:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            # AIのレスポンスをJSONとしてパース
            import json
            data = json.loads(text)
            if isinstance(data, list) and len(data) >= 10:
                print("AIからデータを取得しました。")
                return data[:10]  # 最初の10件
            else:
                print("AIからのレスポンスが不正な形式です。固定データを使用します。")
        except json.JSONDecodeError as e:
            print(f"AIからのレスポンスがJSONではありません: {e}。固定データを使用します。")
    else:
        print(f"AI呼び出しエラー: {result.get('error')}。固定データを使用します。")
    
    # フォールバック: 固定データ
    print("固定データを使用します。")
    return [
        {'comment': '非常に優秀なパフォーマンスを示し、チームに貢献しています。', 'rating': 5},
        {'comment': 'コミュニケーションスキルが優れており、協調性が高いです。', 'rating': 4},
        {'comment': '業務知識が豊富で、問題解決能力が優れています。', 'rating': 5},
        {'comment': '責任感が強く、期限を守って仕事を進めています。', 'rating': 4},
        {'comment': '創造性があり、新しいアイデアを提案してくれます。', 'rating': 4},
        {'comment': 'リーダーシップを発揮し、チームを牽引しています。', 'rating': 5},
        {'comment': '細やかな気配りができ、顧客満足度を高めています。', 'rating': 4},
        {'comment': '効率的に業務を遂行し、生産性を向上させています。', 'rating': 5},
        {'comment': '学習意欲が高く、スキルアップに努めています。', 'rating': 4},
        {'comment': 'ポジティブな姿勢で、周囲に良い影響を与えています。', 'rating': 5}
    ]

def create_sample_data():
    # 社員番号があるスタッフを取得
    staffs = list(Staff.objects.filter(employee_no__isnull=False).exclude(employee_no=''))
    if not staffs:
        print("社員番号があるスタッフが見つかりません。")
        return

    # ユーザーを取得（評価者として）
    User = get_user_model()
    users = list(User.objects.all())
    if not users:
        print("ユーザーが見つかりません。")
        return

    # 評価データ（文言と点数）を取得
    evaluation_data = get_evaluation_data()

    created_count = 0
    for item in evaluation_data:
        comment = item['comment']
        rating = item['rating']
        # 各データに対して10人のスタッフをランダムに選ぶ
        selected_staffs = random.sample(staffs, min(10, len(staffs)))
        for staff in selected_staffs:
            # ランダムな評価日（過去1年以内）
            days_ago = random.randint(0, 365)
            evaluation_date = date.today() - timedelta(days=days_ago)

            # ランダムな評価者
            evaluator = random.choice(users)

            # 評価データ作成
            StaffEvaluation.objects.create(
                staff=staff,
                evaluator=evaluator,
                evaluation_date=evaluation_date,
                rating=rating,
                comment=comment
            )
            created_count += 1

    print(f"{created_count}件のスタッフ評価データを登録しました。")

if __name__ == '__main__':
    create_sample_data()