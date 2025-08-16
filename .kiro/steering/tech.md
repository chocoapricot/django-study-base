# 技術スタック

## フレームワーク & コア
- **Django 5.2.4**: メインWebフレームワーク
- **Python**: バックエンド言語
- **SQLite**: デフォルトデータベース（MySQL設定可能）

## 主要な依存関係
- `django-allauth`: 認証システム（ソーシャル認証対応）
- `django-import-export`: データインポート/エクスポート機能
- `django-currentuser`: モデル内で現在のユーザーを追跡
- `django-concurrency`: 楽観的ロック機能（バージョン管理）
- `pillow`: 画像処理（プロフィール写真）
- `requests`: API呼び出し用HTTPクライアント
- `python-stdnum`: 各種標準番号の検証
- `openpyxl`: Excelファイル処理
- `pymupdf`: PDF処理（pdfrwの代替）
- `mysqlclient`: MySQLデータベースコネクタ（オプション）

## 変更履歴管理システム
- **AppLogモデル**: `apps.system.logs.models.AppLog`で全モデルの変更を統一管理
- **自動記録**: 作成・更新・削除操作を自動的に記録
- **統一表示**: 全ての詳細画面で同じ形式で履歴を表示
- **権限連携**: ユーザー権限と連携した履歴アクセス制御

### ドキュメントと表示
- `home.html`の「Middleware」欄に、利用している主要なコンポーネント（ライブラリ、APIなど）を記載する。**新しいライブラリを追加した場合は、必ずこの欄に追記すること。**

## プロジェクト構造
- **アプリベースアーキテクチャ**: `apps/`ディレクトリ内のモジュラーDjangoアプリ
- **環境固有設定**: 開発/本番用の個別設定ファイル
- **カスタムユーザーモデル**: `apps.accounts.MyUser`による拡張認証

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
python manage.py makemigrations settings
python manage.py makemigrations accounts
python manage.py makemigrations staff
python manage.py makemigrations client
python manage.py makemigrations contract
python manage.py makemigrations company
python manage.py makemigrations connect
python manage.py makemigrations master
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
python manage.py test apps.staff.tests
python manage.py test apps.client.tests
python manage.py test apps.contract.tests
python manage.py test apps.connect.tests
python manage.py test apps.master.tests
python manage.py test apps.api.tests
```

## 環境制約
- **Django Shell制約**: この環境では `python manage.py shell` による対話的実行は利用できません
  - データベース操作やモデルのテストが必要な場合は、テストファイルやビューを通じて実行してください
- **Webインターフェース制約**: Kiroはブラウザ操作ができないため、Webインターフェースでの動作確認はできません
  - `python manage.py runserver` でテストサーバを起動しても、Kiroは画面を確認できません
  - 動作確認は以下の方法で行ってください：
    - **テストケース実行**: `python manage.py test apps.contract.tests`
    - **管理コマンド作成**: カスタム管理コマンドでデータ操作・確認
    - **ログ出力**: print文やloggingでデバッグ情報を出力
    - **データベース直接確認**: `python manage.py dbshell` でSQL実行
    - **データダンプ**: `python manage.py dumpdata` でデータ確認

## 設定メモ
- 設定モジュール: `config.settings.settings`
- 日本語ローカライゼーション（ja-JP、Asia/Tokyo）
- 静的ファイルは`statics/`ディレクトリから配信
- テンプレートは`templates/`ディレクトリにアプリ固有のサブディレクトリで配置