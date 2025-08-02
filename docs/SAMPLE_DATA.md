# サンプルデータ管理ガイド

## 概要

このプロジェクトでは、開発・テスト環境での効率的な動作確認のため、各種サンプルデータを提供しています。

## サンプルデータ一覧

### 基本マスタデータ
- `dropdowns.json`: ドロップダウン選択肢（性別、登録区分、連絡種別等）
- `useradmin.json`: カスタムユーザーデータ

### 業務データ
- `staff.json`: スタッフ（従業員）データ
- `staff_contacted.json`: スタッフ連絡履歴データ（20件）
- `client.json`: クライアント（顧客企業）データ
- `client_contacted.json`: クライアント連絡履歴データ（30件）

## データインポート手順

### 1. 基本マスタデータのインポート（必須）
```bash
# ドロップダウンデータ（最初にインポート）
python manage.py loaddata _sample_data/dropdowns.json

# ユーザーデータ
python manage.py loaddata _sample_data/useradmin.json
```

### 2. 業務データのインポート
```bash
# スタッフデータ
python manage.py loaddata _sample_data/staff.json

# スタッフ連絡履歴データ
python manage.py loaddata _sample_data/staff_contacted.json

# クライアントデータ
python manage.py loaddata _sample_data/client.json

# クライアント連絡履歴データ
python manage.py loaddata _sample_data/client_contacted.json
```

### 3. 全データの一括インポート
```bash
# 全サンプルデータを一括でインポート
python manage.py loaddata _sample_data/*.json
```

## データエクスポート手順

### 個別エクスポート
```bash
# スタッフデータのエクスポート
python manage.py dumpdata staff.staff --format=json --indent=4 > _sample_data/staff.json

# クライアントデータのエクスポート
python manage.py dumpdata client.client --format=json --indent=4 > _sample_data/client.json

# 連絡履歴データのエクスポート
python manage.py dumpdata staff.staffcontacted --format=json --indent=4 > _sample_data/staff_contacted.json
python manage.py dumpdata client.clientcontacted --format=json --indent=4 > _sample_data/client_contacted.json
```

## サンプルデータの特徴

### スタッフ連絡履歴 (staff_contacted.json)
- **件数**: 20件
- **内容**: 面談、書類確認、クレーム対応、問い合わせ対応等
- **対象**: 人材派遣業界での従業員管理に特化

### クライアント連絡履歴 (client_contacted.json)
- **件数**: 30件
- **内容**: 新規案件相談、契約更新、打ち合わせ、クレーム対応等
- **対象企業**: トヨタ自動車、任天堂、Amazon、アステラス製薬等の実在企業
- **業界**: 製造業、IT業界、小売業、公共機関、サービス業

### 連絡種別の分類
| 値 | 名称 | 用途 |
|---|---|---|
| 10 | 問い合わせ | 一般的な質問や相談 |
| 20 | 打ち合わせ | 会議や詳細な相談 |
| 40 | クレーム | 苦情や改善要請 |
| 50 | メール配信 | 一斉送信やお知らせ |

## 注意事項

### インポート順序
1. **ドロップダウンデータを最初にインポート**: 他のデータが参照するため
2. **ユーザーデータを次にインポート**: 作成者・更新者として参照されるため
3. **基本データ（スタッフ・クライアント）をインポート**
4. **関連データ（連絡履歴）を最後にインポート**

### データの整合性
- 外部キー制約により、参照先データが存在しない場合はエラーになります
- 既存データと重複するPKがある場合は、`--ignore`オプションを使用してください

### 本番環境での注意
- サンプルデータは開発・テスト環境でのみ使用してください
- 本番環境では実際のデータを使用し、サンプルデータはインポートしないでください

## トラブルシューティング

### よくあるエラー

#### 外部キー制約エラー
```
django.db.utils.IntegrityError: FOREIGN KEY constraint failed
```
**解決方法**: 参照先データを先にインポートしてください

#### 重複キーエラー
```
django.db.utils.IntegrityError: UNIQUE constraint failed
```
**解決方法**: 既存データを削除するか、`--ignore`オプションを使用してください

#### エンコーディングエラー
```
UnicodeDecodeError: 'utf-8' codec can't decode
```
**解決方法**: ファイルがUTF-8エンコーディングで保存されていることを確認してください

### データのリセット
```bash
# 特定のテーブルのデータを削除
python manage.py shell -c "from apps.staff.models import StaffContacted; StaffContacted.objects.all().delete()"

# データベース全体をリセット（注意：全データが削除されます）
python manage.py flush
```