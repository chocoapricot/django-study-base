# 技術スタック

## フレームワーク & コア
- **Django 5.2.1**: メインWebフレームワーク
- **Python**: バックエンド言語
- **SQLite**: デフォルトデータベース（MySQL設定可能）

## 主要な依存関係
- `django-import-export`: データインポート/エクスポート機能
- `django-currentuser`: モデル内で現在のユーザーを追跡
- `pillow`: 画像処理（プロフィール写真）
- `requests`: API呼び出し用HTTPクライアント
- `openpyxl`: Excelファイル処理
- `pymupdf`: PDF処理（pdfrwの代替）
- `mysqlclient`: MySQLデータベースコネクタ（オプション）

## プロジェクト構造
- **アプリベースアーキテクチャ**: `apps/`ディレクトリ内のモジュラーDjangoアプリ
- **環境固有設定**: 開発/本番用の個別設定ファイル
- **カスタムユーザーモデル**: `apps.system.useradmin.CustomUser`による拡張認証

## よく使うコマンド

### 環境セットアップ
```bash
# 仮想環境をアクティベート
.\venv\Scripts\Activate

# 依存関係のインストール/アップグレード
python.exe -m pip install --upgrade pip
pip list --outdated
pip install --upgrade <package>
```

### データベース操作
```bash
# 全アプリのマイグレーション作成
python manage.py makemigrations dropdowns
python manage.py makemigrations useradmin
python manage.py makemigrations menu
python manage.py makemigrations parameters
python manage.py makemigrations staff
python manage.py makemigrations client
python manage.py makemigrations common
python manage.py makemigrations
python manage.py migrate

# スーパーユーザー作成
python manage.py createsuperuser

# データベースシェルアクセス
python manage.py dbshell
```

### データ管理
```bash
# JSONへのデータエクスポート
python manage.py dumpdata <app> --format=json --indent=4 > _sample_data/<app>.json

# JSONからのデータインポート（UTF-8エンコーディング確認）
python manage.py loaddata _sample_data/<app>.json
```

### 開発
```bash
# 開発サーバー起動
python manage.py runserver

# テスト実行
python manage.py test apps.api.tests
```

## 設定メモ
- 設定モジュール: `config.settings.settings`
- 日本語ローカライゼーション（ja-JP、Asia/Tokyo）
- 静的ファイルは`statics/`ディレクトリから配信
- テンプレートは`templates/`ディレクトリにアプリ固有のサブディレクトリで配置