# メニュー設定手順

勤怠管理アプリケーションをメニューに追加するには、Django管理画面から以下の設定を行ってください。

## 管理画面でのメニュー追加手順

1. Django管理画面にアクセス: `http://localhost:8000/admin/`
2. 「システム設定」→「メニュー」を選択
3. 「メニューを追加」ボタンをクリック

## 追加するメニュー項目

### 1. 勤怠管理（親メニュー）

```
表示名: 勤怠管理
URL: /kintai/
アイコン: bi-clock-history
アイコンスタイル: （空欄）
親メニュー: （なし）
階層レベル: 0
完全一致: チェックなし
必要な権限: kintai.view_stafftimesheet
表示順: 70
有効: チェック
```

### 2. 月次勤怠一覧（子メニュー）

```
表示名: 月次勤怠一覧
URL: /kintai/timesheet/
アイコン: bi-calendar-month
アイコンスタイル: （空欄）
親メニュー: 勤怠管理
階層レベル: 1
完全一致: チェックなし
必要な権限: kintai.view_stafftimesheet
表示順: 10
有効: チェック
```

## SQLで直接追加する場合

```sql
-- 親メニュー（勤怠管理）
INSERT INTO apps_system_menu (name, url, icon, icon_style, parent_id, level, exact_match, required_permission, disp_seq, active, created_at, updated_at)
VALUES ('勤怠管理', '/kintai/', 'bi-clock-history', '', NULL, 0, 0, 'kintai.view_stafftimesheet', 70, 1, datetime('now'), datetime('now'));

-- 子メニュー（月次勤怠一覧）
-- 注意: parent_idには上で作成した親メニューのIDを指定してください
INSERT INTO apps_system_menu (name, url, icon, icon_style, parent_id, level, exact_match, required_permission, disp_seq, active, created_at, updated_at)
VALUES ('月次勤怠一覧', '/kintai/timesheet/', 'bi-calendar-month', '', (SELECT id FROM apps_system_menu WHERE name = '勤怠管理'), 1, 0, 'kintai.view_stafftimesheet', 10, 1, datetime('now'), datetime('now'));
```

## 権限の確認

メニューを表示するには、ユーザーに以下の権限が必要です：

- `kintai.view_stafftimesheet`: 月次勤怠の閲覧権限

管理画面の「ユーザー」または「グループ」から権限を付与してください。

## アイコンについて

使用しているアイコンは Bootstrap Icons です：
- `bi-clock-history`: 時計と履歴のアイコン
- `bi-calendar-month`: カレンダーのアイコン

他のアイコンを使用したい場合は、[Bootstrap Icons](https://icons.getbootstrap.com/) から選択してください。
