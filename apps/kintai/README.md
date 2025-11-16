# 勤怠管理アプリケーション (apps.kintai)

## 概要
スタッフの日々の勤怠と月次勤怠を管理するアプリケーションです。スタッフ契約に紐づいて、毎月の勤怠情報を作成・管理します。

## モデル構成

### StaffTimesheet（月次勤怠）
スタッフ契約に対して毎月作成される月次勤怠情報を管理します。

**主要フィールド:**
- `staff_contract`: スタッフ契約（外部キー）
- `staff`: スタッフ（外部キー）
- `year`: 対象年
- `month`: 対象月（1-12）
- `status`: ステータス（作成中/提出済み/承認済み/差戻し）
- `total_work_days`: 出勤日数
- `total_work_hours`: 総労働時間
- `total_overtime_hours`: 残業時間
- `total_holiday_work_hours`: 休日労働時間
- `total_late_minutes`: 遅刻時間（分）
- `total_early_leave_minutes`: 早退時間（分）
- `total_absence_days`: 欠勤日数
- `total_paid_leave_days`: 有給休暇日数

**制約:**
- `staff_contract`, `year`, `month` の組み合わせで一意

**主要メソッド:**
- `calculate_totals()`: 日次勤怠データから集計値を計算
- `is_editable`: 編集可能かどうかを判定
- `is_submitted`: 提出済みかどうかを判定
- `is_approved`: 承認済みかどうかを判定

### StaffTimecard（日次勤怠）
月次勤怠に紐づく日々の勤怠情報を管理します。

**主要フィールド:**
- `timesheet`: 月次勤怠（外部キー）
- `work_date`: 勤務日
- `work_type`: 勤務区分（出勤/休日/欠勤/有給休暇/特別休暇/代休/稼働無し）
- `start_time`: 出勤時刻
- `end_time`: 退勤時刻
- `break_minutes`: 休憩時間（分）
- `work_hours`: 労働時間（自動計算）
- `overtime_hours`: 残業時間（自動計算）
- `holiday_work_hours`: 休日労働時間（自動計算）
- `late_minutes`: 遅刻時間（分、自動計算）
- `early_leave_minutes`: 早退時間（分、自動計算）
- `paid_leave_days`: 有給休暇日数（0.5または1.0）

**制約:**
- `timesheet`, `work_date` の組み合わせで一意

**主要メソッド:**
- `calculate_work_hours()`: 労働時間を自動計算（保存時に実行）
- `is_holiday`: 休日かどうかを判定
- `is_absence`: 欠勤かどうかを判定
- `work_hours_display`: 労働時間の表示用文字列

## データベーステーブル
- `apps_kintai_staff_timesheet`: 月次勤怠
- `apps_kintai_staff_timecard`: 日次勤怠

## URL構成
```
/kintai/timesheet/                      # 月次勤怠一覧
/kintai/timesheet/create/               # 月次勤怠作成
/kintai/timesheet/<pk>/                 # 月次勤怠詳細
/kintai/timesheet/<pk>/edit/            # 月次勤怠編集
/kintai/timesheet/<pk>/delete/          # 月次勤怠削除
/kintai/timecard/<timesheet_pk>/create/ # 日次勤怠作成
/kintai/timecard/<pk>/edit/             # 日次勤怠編集
/kintai/timecard/<pk>/delete/           # 日次勤怠削除
```

## 使用方法

### マイグレーション
```bash
python manage.py makemigrations kintai
python manage.py migrate kintai
```

### テスト実行
```bash
python manage.py test apps.kintai.tests
```

## 機能の特徴

### 自動計算機能
- 労働時間の自動計算（出勤時刻、退勤時刻、休憩時間から算出）
- 残業時間の自動計算（所定労働時間8時間を超過した分）
- 休日労働時間の自動判定（土日の勤務）
- 遅刻・早退時間の自動計算（標準時刻9:00-18:00との比較）

### ワークフロー
1. 月次勤怠を作成（スタッフ契約、年月を指定）
2. 日次勤怠を登録（勤務日ごとに出退勤時刻を入力）
3. 月次勤怠の集計値を計算（`calculate_totals()`メソッド）
4. 提出・承認フロー（作成中→提出済み→承認済み）

### バリデーション
- 月の範囲チェック（1-12）
- 出勤時は出勤・退勤時刻が必須
- 退勤時刻は出勤時刻より後
- 有給休暇時は日数が必須
- スタッフ契約とスタッフの整合性チェック

## 実装済み機能

### フォーム
- ✅ 月次勤怠フォーム（`StaffTimesheetForm`）
- ✅ 日次勤怠フォーム（`StaffTimecardForm`）

### テンプレート
- ✅ 月次勤怠一覧画面（`timesheet_list.html`）
- ✅ 月次勤怠作成・編集画面（`timesheet_form.html`）
- ✅ 月次勤怠詳細画面（`timesheet_detail.html`）
- ✅ 月次勤怠削除確認画面（`timesheet_delete.html`）
- ✅ 日次勤怠作成・編集画面（`timecard_form.html`）
- ✅ **日次勤怠カレンダー入力画面（`timecard_calendar.html`）**
- ✅ 日次勤怠削除確認画面（`timecard_delete.html`）

### ビュー
- ✅ 月次勤怠の作成・編集・削除機能
- ✅ 日次勤怠の作成・編集・削除機能
- ✅ **日次勤怠のカレンダー形式一括入力機能**
- ✅ 月次勤怠の自動集計機能（日次勤怠の変更時に自動更新）
- ✅ 編集可能状態の判定（提出済み・承認済みは編集不可）

### メニュー
- ✅ 勤怠管理メニュー（親メニュー）
- ✅ 月次勤怠一覧メニュー（子メニュー）

### テスト
- ✅ モデルテスト（11件）
- ✅ ビューテスト（9件）
- ✅ メニューテスト（3件）
- ✅ フォームテスト（6件）
- 合計29件のテストがすべて成功

### その他
- ✅ 管理画面（admin.py）を削除（不要なため）
- ✅ 勤務区分に応じた入力欄の動的表示（JavaScript）
- ✅ カレンダー入力の便利機能：
  - 平日出勤・休日稼働無で一括設定（平日：9:00-18:00休憩60分、土日祝日：稼働無し）
  - 全てクリア
- ✅ 土日祝日の背景色表示（土曜：青、日曜・祝日：赤）
- ✅ 時間表記を「8時間00分」形式で統一

## カレンダー入力機能の特徴

### 一括入力
- 月全体の勤怠データを1画面で入力可能
- 縦にスクロールして日付順に入力
- 土日は背景色で区別（土曜：青、日曜：赤）

### 便利機能
1. **平日出勤・休日稼働無で埋める**: ワンクリックで平日を出勤（9:00-18:00、休憩60分）、土日祝日を稼働無しで一括設定
2. **全てクリア**: 全ての入力をクリア

### 自動制御
- 勤務区分に応じて入力欄を自動的に有効/無効化
  - 出勤: 時刻と休憩時間を入力
  - 有給休暇: 有給日数を入力
  - その他: 入力欄を無効化

### リアルタイム表示
- 労働時間と残業時間を自動計算して表示（保存後）

## 今後の拡張予定
- 月次勤怠の自動作成機能（契約から自動生成）
- 勤怠データのエクスポート機能（CSV、Excel）
- 勤怠レポート機能（月次・年次集計）
- 承認ワークフロー機能の強化（提出・承認・差戻し）
- 勤怠データの集計・分析機能
- カレンダー入力画面でのリアルタイム計算表示
