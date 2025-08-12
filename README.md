# Django Study Base

Django学習用のプロジェクトです。スタッフ管理とクライアント管理機能を持つビジネス管理システムを通じて、Djangoの基本的な機能から応用まで学習することを目的としています。Django 5.2.4をベースに構築され、日本語環境に最適化されています。

> **注意**: このプロジェクトは個人の学習目的で作成されており、実際のビジネス用途での使用は想定していません。

## 🚀 主な機能

### 📊 管理機能
- **スタッフ管理**: 従業員データの管理と追跡、資格・スキルとの紐付け
- **クライアント管理**: 顧客関係管理機能、部署・担当者との紐付け
- **契約管理**: クライアント契約・スタッフ契約の管理、契約状況の追跡
- **会社・部署管理**: 会社情報と部署の体系的管理
- **連絡履歴管理**: スタッフ・クライアントとの連絡記録
- **マスター管理**: 資格、スキル、支払いサイト、振込先銀行などのマスターデータ管理

### 🔐 認証・セキュリティ
- **カスタムユーザー認証**: django-allauthベースの認証システム
- **ロールベースアクセス制御**: 権限管理機能
- **パスワードバリデーション**: カスタムパスワード要件

### 🛠️ システム管理
- **ドロップダウン管理**: 選択肢の動的管理
- **パラメータ管理**: システム設定の管理
- **メニュー管理**: ナビゲーション設定
- **変更履歴管理**: 統一されたAppLogシステムによる全データの変更追跡

### 📱 UI/UX
- **レスポンシブデザイン**: Bootstrap 5ベース
- **日本語対応**: 完全な日本語ローカライゼーション
- **直感的なインターフェース**: 使いやすいUI設計

## 🛠️ 技術スタック

### フレームワーク & コア
- **Django 5.2.4**: メインWebフレームワーク
- **Python 3.12**: バックエンド言語
- **SQLite**: デフォルトデータベース（MySQL対応可能）

### 主要な依存関係
- `django-allauth`: 認証システム
- `django-import-export`: データインポート/エクスポート
- `django-currentuser`: 現在のユーザー追跡
- `pillow`: 画像処理
- `openpyxl`: Excelファイル処理
- `PyMuPDF`: PDF処理
- `requests`: HTTP通信
- `python-stdnum`: 各種標準番号の検証

### フロントエンド
- **Bootstrap 5**: UIフレームワーク
- **Bootstrap Icons**: アイコンセット
- **レスポンシブデザイン**: モバイル対応

## 📁 プロジェクト構造

```
django-study-base/
├── apps/                    # Djangoアプリケーション
│   ├── system/             # システム管理
│   │   ├── settings/       # 設定管理 (ドロップダウン、メニュー、パラメータ、ログを統合)
│   │   └── useradmin/      # ユーザー管理
│   ├── master/             # マスター管理
│   ├── staff/              # スタッフ管理
│   ├── client/             # クライアント管理
│   ├── contract/           # 契約管理
│   ├── company/            # 会社・部署管理
│   ├── accounts/           # 認証システム
│   ├── common/             # 共通機能
│   └── api/                # REST API
├── config/                 # プロジェクト設定
├── templates/              # HTMLテンプレート
├── statics/                # 静的ファイル
├── _sample_data/           # サンプルデータ
├── _scripts/               # 管理・運用スクリプト
├── _docs/                  # ドキュメント
└── requirements.txt        # 依存関係
```

## データベーステーブル一覧

| テーブル名 | 説明 |
| --- | --- |
| `apps_client` | クライアント |
| `apps_client_contacted` | クライアント連絡履歴 |
| `apps_client_file` | クライアントファイル |
| `apps_staff` | スタッフ |
| `apps_staff_contacted` | スタッフ連絡履歴 |
| `apps_staff_qualification` | スタッフ保有資格 |
| `apps_staff_skill` | スタッフ保有スキル |
| `apps_staff_file` | スタッフファイル |
| `apps_contract_client` | クライアント契約 |
| `apps_contract_staff` | スタッフ契約 |
| `apps_company` | 会社 |
| `apps_company_department` | 部署 |
| `apps_master_qualification` | 資格マスター（カテゴリと資格） |
| `apps_master_skill` | 技能マスター（カテゴリと技能） |
| `apps_master_bill_payment` | 支払いサイトマスター |
| `apps_master_bill_bank` | 振込先銀行マスター |
| `apps_system_dropdowns` | ドロップダウン設定 |
| `apps_system_parameter` | パラメータ設定 |
| `apps_system_menu` | メニュー設定 |
| `apps_system_mail_log` | メール送信ログ |
| `apps_system_app_log` | アプリケーション操作ログ |
| `auth_user` | カスタムユーザー |

## 🚀 セットアップ

### 前提条件
- Python 3.12以上
- pip（Python パッケージマネージャー）

### インストール手順

1. **プロジェクトのダウンロード**
```bash
# GitHubからダウンロードまたはクローン
git clone [このリポジトリのURL]
cd django-study-base
```

2. **仮想環境の作成とアクティベート**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **依存関係のインストール**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **データベースのセットアップ**
```bash
# 自動セットアップ（推奨）
python _scripts/reset_database.py

# または手動セットアップ
python manage.py makemigrations
python manage.py migrate
```

5. **スーパーユーザーの作成**
```bash
python manage.py createsuperuser
```

6. **サンプルデータのインポート（オプション）**
```bash
python _scripts/load_sample_data.py
```

7. **開発サーバーの起動**
```bash
python manage.py runserver
```

7. **ブラウザでアクセス**
```
http://127.0.0.1:8000/
```

## 📋 変更履歴管理

### 統一された履歴管理システム
このアプリケーションでは、すべてのデータ変更を統一されたシステムで追跡しています：

- **AppLogモデル**: 全モデルの作成・更新・削除操作を記録
- **統一された表示**: スタッフ、クライアント、契約すべてで同じ形式で履歴表示
- **詳細画面統合**: 各詳細画面の下部に変更履歴セクションを表示
- **操作者追跡**: 誰がいつ何を変更したかを記録
- **バージョン管理**: django-concurrencyと連携した楽観的ロック

### 履歴表示項目
- **対象**: 変更されたモデル（基本情報、資格、技能、契約情報など）
- **操作**: 作成・編集・削除（色分けされたバッジで表示）
- **変更内容**: オブジェクトの文字列表現
- **変更者**: 操作を行ったユーザー
- **日時**: YYYY/MM/DD HH:MM:SS形式での記録

## 🧪 テスト

### テストの実行
```bash
# 全テストの実行
python manage.py test

# 特定のアプリのテスト
python manage.py test apps.staff.tests
python manage.py test apps.client.tests
python manage.py test apps.contract.tests

# 特定のテストファイル実行
python manage.py test apps.staff.tests.test_staff_form

# 詳細出力でのテスト実行
python manage.py test --verbosity=2
```

### テストガイドライン
プロジェクトのテスト構成とルールについては、[テストガイドライン](docs/testing-guidelines.md)を参照してください。

### テストカバレッジ
- 認証システム: ✅ 完全対応
- スタッフ管理: ✅ CRUD操作テスト、フォームバリデーション
- クライアント管理: ✅ CRUD操作テスト
- 契約管理: ✅ CRUD操作テスト、フォーム表示機能
- API エンドポイント: ✅ 基本テスト

## 📊 データ管理

### データのエクスポート
```bash
python manage.py dumpdata staff    --format=json --indent=4 > _sample_data/staff.json
python manage.py dumpdata client   --format=json --indent=4 > _sample_data/client.json
python manage.py dumpdata contract --format=json --indent=4 > _sample_data/contract.json
python manage.py dumpdata company  --format=json --indent=4 > _sample_data/company.json
python manage.py dumpdata master   --format=json --indent=4 > _sample_data/master.json
```

### データのインポート
```bash
python manage.py loaddata _sample_data/staff.json
python manage.py loaddata _sample_data/client.json
python manage.py loaddata _sample_data/contract.json
python manage.py loaddata _sample_data/company.json
python manage.py loaddata _sample_data/master.json
```

## 🔧 設定

### 環境設定
- **開発環境**: `config/settings/settings.py`
- **テスト環境**: `config/settings/test.py`
- **本番環境**: `config/settings/product.py`

### 主要設定項目
```python
# 言語・タイムゾーン
LANGUAGE_CODE = 'ja-JP'
TIME_ZONE = 'Asia/Tokyo'

# 認証設定
AUTH_USER_MODEL = 'useradmin.CustomUser'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'

# メール設定（開発環境）
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## 🌐 API

### REST APIエンドポイント
- `/api/staff/` - スタッフ管理API
- `/api/client/` - クライアント管理API
- `/api/contract/` - 契約管理API
- `/api/company/` - 会社・部署管理API

### 認証
- django-allauthベースの認証
- セッション認証対応

## 🎨 UI/UX

### デザインシステム
- **カラーパレット**: Bootstrap 5準拠
- **タイポグラフィ**: 日本語フォント最適化
- **レスポンシブ**: モバイルファースト設計

### アクセシビリティ
- WCAG 2.1準拠
- キーボードナビゲーション対応
- スクリーンリーダー対応

## 🚀 デプロイ

### 本番環境での設定
1. 環境変数の設定
2. データベースの設定（MySQL推奨）
3. 静的ファイルの収集
4. WSGIサーバーの設定

```bash
# 静的ファイルの収集
python manage.py collectstatic

# 本番用データベースマイグレーション
python manage.py migrate --settings=config.settings.product
```

## 📝 ライセンス


このプロジェクトは学習目的で作成されており、個人利用に限定されます。

---

**Django Study Base** - Django学習のための実践プロジェクト 📚