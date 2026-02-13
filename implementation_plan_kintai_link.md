# 勤怠打刻申請詳細画面のリンク改善計画

## 概要
勤怠打刻申請詳細画面（`/kintai/timerecord/approval/<pk>/`）におけるリンクの挙動とデザインを改善します。

## 変更内容

### 1. 勤怠打刻申請詳細テンプレート (`templates/kintai/timerecord_approval_detail.html`)
- **スタッフリンク**: 別ウィンドウで開くことを示すアイコン (`bi-box-arrow-up-right`) を追加します。
- **スタッフ契約リンク**: 別ウィンドウで開くことを示すアイコン (`bi-box-arrow-up-right`) を追加します。
- **打刻詳細リンク**:
    - `target="_blank"` を削除し、同一ウィンドウで遷移するように変更します。
    - アイコンを `bi-box-arrow-up-right` から `bi-eye` (詳細表示) に変更します。

### 2. 勤怠打刻詳細テンプレート (`templates/kintai/timerecord_detail.html`)
- **戻るボタン**: 遷移元に戻れるように、`javascript:history.back();` を利用するように変更します。これにより、カレンダーから来た場合も承認詳細から来た場合も適切に戻れるようになります。

## 実施手順
1. `templates/kintai/timerecord_approval_detail.html` の修正。
2. `templates/kintai/timerecord_detail.html` の修正。
3. 動作確認。
