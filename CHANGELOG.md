# 変更履歴 (CHANGELOG)

このファイルは、プロジェクトの重要な変更を記録します。

## [2025-08-03] - Django 5.2.4アップデート

### 追加 (Added)
- `pytest==8.4.1`をrequirements.txtに追加
- 変更管理文書（CHANGELOG.md）を新規作成

### 変更 (Changed)
- Django 5.2.1 → 5.2.4にアップデート
- README.mdでDjangoバージョン表記を5.2.4に更新
- .kiro/steering/tech.mdでDjangoバージョン表記を5.2.4に更新
- requirements.txtにpytestを追加して実際の環境と整合

### 修正 (Fixed)
- `common_applog`テーブル削除マイグレーションの問題を解決
- マイグレーション`apps/common/migrations/0005_delete_applog.py`を偽装適用で修正

### 技術的詳細
- Django 5.2.4では、セキュリティ修正とバグ修正が含まれています
- AppLogモデルは`apps.system.logs.models.AppLog`に移行済み
- 旧`common.AppLog`は完全に削除され、新しいログシステムを使用

### 影響範囲
- 既存のコードとの互換性は保たれています
- データベーススキーマの変更はありません（マイグレーション適用済み）
- 新規環境でのセットアップ手順に変更はありません

---

## 変更管理について

### バージョニング
このプロジェクトは学習目的のため、セマンティックバージョニングではなく日付ベースの変更管理を採用しています。

### 変更カテゴリ
- **追加 (Added)**: 新機能
- **変更 (Changed)**: 既存機能の変更
- **非推奨 (Deprecated)**: 将来削除予定の機能
- **削除 (Removed)**: 削除された機能
- **修正 (Fixed)**: バグ修正
- **セキュリティ (Security)**: セキュリティ関連の修正