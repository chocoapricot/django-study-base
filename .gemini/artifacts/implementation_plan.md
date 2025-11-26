# 日次勤怠カレンダー入力に就業時間プルダウン追加

## 概要
日次勤怠カレンダー入力画面（URL: `/kintai/timecard/calendar/initial/{contract_pk}/{target_month}/`）に、勤務区分の左に就業時間プルダウンを追加します。このプルダウンは、スタッフ契約に設定されている就業時間パターンの勤務時間一覧を表示し、選択すると自動的に勤務区分を「出勤」にし、開始時刻・終了時刻・休憩時間を設定します。

## 要件
1. **プルダウンの表示位置**: 勤務区分の左に配置
2. **プルダウンの内容**: スタッフ契約の`worktime_pattern`に紐づく`WorkTimePatternWork`の一覧
3. **プルダウンの名称**: `time_name.content`（勤務時間名称）を表示
4. **選択時の動作**:
   - 勤務区分を「10」（出勤）に設定
   - 開始時刻を`start_time`に設定
   - 終了時刻を`end_time`に設定
   - 休憩時間を`break_times`の合計に設定

## データ構造
- `StaffContract.worktime_pattern` → `WorkTimePattern`
- `WorkTimePattern.work_times` → `WorkTimePatternWork[]`
- `WorkTimePatternWork`:
  - `time_name`: `PhraseTemplate` (表示名称)
  - `start_time`: `TimeField`
  - `end_time`: `TimeField`
  - `start_time_next_day`: `BooleanField`
  - `end_time_next_day`: `BooleanField`
  - `break_times`: `WorkTimePatternBreak[]`
- `WorkTimePatternBreak`:
  - `start_time`: `TimeField`
  - `end_time`: `TimeField`
  - `start_time_next_day`: `BooleanField`
  - `end_time_next_day`: `BooleanField`

## 実装手順

### 1. ビュー（views.py）の修正
#### 1.1 `timecard_calendar_initial` ビュー
- コンテキストに`work_times_data`を追加
- 契約の`worktime_pattern`から`work_times`を取得
- 各`work_time`について以下の情報をJSON形式で渡す:
  - `id`: WorkTimePatternWork.id
  - `name`: time_name.content
  - `start_time`: start_time (HH:MM形式)
  - `end_time`: end_time (HH:MM形式)
  - `start_time_next_day`: boolean
  - `end_time_next_day`: boolean
  - `break_minutes`: break_timesの合計分数

#### 1.2 `staff_timecard_calendar` ビュー
- 同様に`work_times_data`を追加（スタッフ別カレンダー入力でも使用）

### 2. テンプレート（timecard_calendar.html）の修正
#### 2.1 テーブルヘッダーの追加
- 「勤務日」と「勤務区分」の間に「就業時間」列を追加

#### 2.2 各行に就業時間プルダウンを追加
```html
<td>
    <select name="work_time_{{ data.day }}" class="form-select form-select-sm work-time-select" data-day="{{ data.day }}">
        <option value="">-</option>
        {% for wt in work_times %}
        <option value="{{ wt.id }}">{{ wt.name }}</option>
        {% endfor %}
    </select>
</td>
```

#### 2.3 JavaScriptの追加
- 就業時間プルダウンの変更イベントハンドラを追加
- 選択時の処理:
  1. 勤務区分を「10」（出勤）に設定
  2. 開始時刻・終了時刻・休憩時間を設定
  3. 翌日フラグを設定
  4. `toggleFields()`を呼び出して入力欄を有効化

### 3. スタッフ別カレンダー入力（staff_timecard_calendar.html）の修正
- 同様の修正を適用

## テスト計画
1. **就業時間パターンが設定されている契約**:
   - プルダウンに勤務時間一覧が表示されることを確認
   - 選択時に時刻が正しく設定されることを確認
   - 休憩時間が正しく計算されることを確認
   - 翌日フラグが正しく設定されることを確認

2. **就業時間パターンが設定されていない契約**:
   - プルダウンが空（選択肢なし）で表示されることを確認

3. **複数の勤務時間が設定されている場合**:
   - すべての勤務時間が表示されることを確認
   - 表示順が`display_order`に従っていることを確認

4. **既存機能との互換性**:
   - 「契約通り」ボタンが正常に動作することを確認
   - 手動入力も引き続き可能であることを確認

## 影響範囲
- `apps/kintai/views.py`: `timecard_calendar_initial`, `staff_timecard_calendar`
- `templates/kintai/timecard_calendar.html`
- `templates/kintai/staff_timecard_calendar.html`

## 注意事項
- 既存のデフォルト値設定（`_get_contract_work_time`）は維持
- 就業時間プルダウンは補助機能として、手動入力も引き続き可能
- 翌日フラグの処理を正しく実装する必要がある
