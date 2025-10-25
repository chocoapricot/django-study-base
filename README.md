# Django Study Base

Django学習用のプロジェクトです。スタッフ管理とクライアント管理機能を持つビジネス管理システムを通じて、Djangoの基本的な機能から応用まで学習することを目的としています。Django 5.2.5をベースに構築され、日本語環境に最適化されています。

> **注意**: このプロジェクトは個人の学習目的で作成されており、実際のビジネス用途での使用は想定していません。

## 🚀 主な機能

### 📊 管理機能
- **スタッフ管理**: 従業員データの管理と追跡、資格・スキルとの紐付け
- **クライアント管理**: 顧客関係管理機能、部署・担当者との紐付け
- **契約管理**: クライアント契約・スタッフ契約の管理、契約状況の追跡
- **会社・部署管理**: 会社情報と部署の体系的管理
- **連絡履歴管理**: スタッフ・クライアントとの連絡記録
- **接続管理**: スタッフ・クライアント担当者との接続申請・承認機能
- **マスター管理**: 資格、スキル、支払条件、銀行などの各種マスターデータを一元的に管理します。各マスタはカテゴリ別に整理され、統一されたリスト画面から各管理ページにアクセスできます。
- **プロフィール管理**: ユーザープロファイル、マイナンバー管理

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
- **ロジック情報表示**: ページ固有のバリデーションロジックをモーダルで表示

## 🛠️ 技術スタック

### フレームワーク & コア
- **Django 5.2.5**: メインWebフレームワーク
- **Python 3.12**: バックエンド言語
- **SQLite**: デフォルトデータベース（MySQL対応可能）

### 主要な依存関係
- `django-allauth`: 認証システム
- `django-import-export`: データインポート/エクスポート
- `django-currentuser`: 現在のユーザー追跡
- `pillow`: 画像処理
- `openpyxl`: Excelファイル処理
- `PyMuPDF`: PDF処理
- `reportlab`: PDF処理
- `requests`: HTTP通信
- `python-stdnum`: 各種標準番号の検証

### フロントエンド
- **Bootstrap 5**: UIフレームワーク
- **Bootstrap Icons**: アイコンセット
- **レスポンシブデザイン**: モバイル対応

## 📁 プロジェクト構造

```
django-study-base/
├── _docs/                  # ドキュメント
├── _sample_data/           # サンプルデータ
├── _scripts/               # 管理・運用スクリプト
│
├── apps/                   # Djangoアプリケーション
│   ├── accounts/           # ユーザー管理・認証
│   ├── api/                # REST API
│   ├── client/             # クライアント管理
│   ├── common/             # 共通機能
│   ├── company/            # 会社・部署管理
│   ├── connect/            # 接続管理 (スタッフ・クライアント接続申請)
│   ├── contract/           # 契約管理
│   ├── csstest/            # CSSテスト・開発
│   ├── home/               # ホームページ
│   ├── master/             # マスター管理 (資格、スキル、銀行、支払条件)
│   ├── profile/            # プロフィール管理
│   ├── staff/              # スタッフ管理
│   └── system/             # システム管理
│       ├── logs/           # ログ管理 (アプリログ、メールログ)
│       ├── settings/       # 設定管理 (ドロップダウン、メニュー、パラメータ)
│       └── tables/         # テーブル管理
├── config/                 # プロジェクト設定
├── media/                  # アップロードされたファイル
│   ├── client_files/       # クライアントアップロードファイル
│   │   └── {クライアントID}/
│   └── staff_files/        # スタッフアップロードファイル
│       └── {スタッフID}/
├── statics/                # 静的ファイル
└── templates/              # HTMLテンプレート
```

## データベーステーブル一覧（94テーブル）

### 本アプリケーション独自テーブル（76テーブル）

| テーブル名 | モデル名 | 説明 |
| --- | --- | --- |
| `accounts_myuser` | `MyUser` | カスタムユーザー（メインテーブル） |
| `apps_client` | `Client` | クライアント基本情報 |
| `apps_client_contacted` | `ClientContacted` | クライアント連絡履歴 |
| `apps_client_department` | `ClientDepartment` | クライアント部署情報 |
| `apps_client_file` | `ClientFile` | クライアントファイル |
| `apps_client_user` | `ClientUser` | クライアント担当者 |
| `apps_company` | `Company` | 会社情報 |
| `apps_company_department` | `CompanyDepartment` | 部署情報 |
| `apps_company_user` | `CompanyUser` | 会社担当者 |
| `apps_connect_bank_request` | `BankRequest` | 銀行口座変更申請 |
| `apps_connect_client` | `ConnectClient` | クライアント接続申請 |
| `apps_connect_contact_request` | `ContactRequest` | 連絡先変更申請 |
| `apps_connect_disability_request` | `DisabilityRequest` | 障害者情報変更申請 |
| `apps_connect_international_request` | `ConnectInternationalRequest` | 国際情報変更申請 |
| `apps_connect_mynumber_request` | `MynumberRequest` | マイナンバー接続申請 |
| `apps_connect_profile_request` | `ProfileRequest` | プロフィール変更申請 |
| `apps_connect_staff` | `ConnectStaff` | スタッフ接続申請 |
| `apps_connect_staff_agree` | `ConnectStaffAgree` | スタッフ同意 |
| `apps_contract_assignment` | `ContractAssignment` | 契約割り当て |
| `apps_contract_client` | `ClientContract` | クライアント契約 |
| `apps_contract_client_haken` | `ClientContractHaken` | クライアント契約派遣情報 |
| `apps_contract_client_haken_exempt` | `ClientContractHakenExempt` | クライアント契約派遣抵触日制限外情報 |
| `apps_contract_client_number` | `ClientContractNumber` | クライアント契約番号 |
| `apps_contract_client_print` | `ClientContractPrint` | クライアント契約書発行履歴 |
| `apps_contract_client_ttp` | `ClientContractTtp` | クライアント契約紹介予定派遣情報 |
| `apps_contract_staff` | `StaffContract` | スタッフ契約 |
| `apps_contract_staff_number` | `StaffContractNumber` | スタッフ契約番号 |
| `apps_contract_staff_print` | `StaffContractPrint` | スタッフ契約書発行履歴 |
| `apps_contract_staff_teishokubi` | `StaffContractTeishokubi` | スタッフの個人抵触日 |
| `apps_contract_staff_teishokubi_detail` | `StaffContractTeishokubiDetail` | 個人抵触日算出詳細 |
| `apps_master_bank` | `Bank` | 銀行マスター |
| `apps_master_bank_branch` | `BankBranch` | 銀行支店マスター |
| `apps_master_bill_bank` | `BillBank` | 会社銀行マスター |
| `apps_master_bill_payment` | `BillPayment` | 支払条件マスター |
| `apps_master_client_regist_status` | `ClientRegistStatus` | クライアント登録状況 |
| `apps_master_contract_pattern` | `ContractPattern` | 契約書パターンマスター |
| `apps_master_contract_terms` | `ContractTerms` | 契約文言マスター |
| `apps_master_default_value` | `DefaultValue` | デフォルト値マスター |
| `apps_master_employment_type` | `EmploymentType` | 雇用形態マスター |
| `apps_master_information` | `Information` | お知らせマスター |
| `apps_master_information_file` | `InformationFile` | お知らせファイル |
| `apps_master_job_category` | `JobCategory` | 職種マスター |
| `apps_master_mail_template` | `MailTemplate` | メールテンプレート |
| `apps_master_minimum_pay` | `MinimumPay` | 最低賃金マスター |
| `apps_master_phrase_template` | `PhraseTemplate` | 汎用文言テンプレート |
| `apps_master_qualification` | `Qualification` | 資格マスター |
| `apps_master_skill` | `Skill` | 技能マスター |
| `apps_master_staff_agreement` | `StaffAgreement` | スタッフ同意書マスター |
| `apps_master_staff_regist_status` | `StaffRegistStatus` | スタッフ登録状況 |
| `apps_profile_staff` | `StaffProfile` | スタッフプロフィール |
| `apps_profile_staff_bank` | `StaffProfileBank` | プロフィール銀行口座 |
| `apps_profile_staff_contacts` | `StaffProfileContact` | プロフィール連絡先 |
| `apps_profile_staff_disability` | `StaffProfileDisability` | プロフィール障害者情報 |
| `apps_profile_staff_international` | `StaffProfileInternational` | プロフィール外国籍情報 |
| `apps_profile_staff_mynumber` | `StaffProfileMynumber` | プロフィールマイナンバー |
| `apps_profile_staff_qualification` | `StaffProfileQualification` | プロフィール保有資格 |
| `apps_profile_staff_skill` | `StaffProfileSkill` | プロフィール保有スキル |
| `apps_staff` | `Staff` | スタッフ基本情報 |
| `apps_staff_bank` | `StaffBank` | スタッフ銀行口座 |
| `apps_staff_contacted` | `StaffContacted` | スタッフ連絡履歴 |
| `apps_staff_contacts` | `StaffContact` | スタッフ連絡先 |
| `apps_staff_disability` | `StaffDisability` | スタッフ障害者情報 |
| `apps_staff_file` | `StaffFile` | スタッフファイル |
| `apps_staff_international` | `StaffInternational` | スタッフ外国籍情報 |
| `apps_staff_mynumber` | `StaffMynumber` | スタッフマイナンバー |
| `apps_staff_payroll` | `StaffPayroll` | スタッフ給与 |
| `apps_staff_qualification` | `StaffQualification` | スタッフ保有資格 |
| `apps_staff_skill` | `StaffSkill` | スタッフ保有スキル |
| `apps_system_access_log` | `AccessLog` | アクセスログ |
| `apps_system_app_log` | `AppLog` | アプリケーション操作ログ |
| `apps_system_dropdowns` | `Dropdowns` | ドロップダウン設定 |
| `apps_system_mail_log` | `MailLog` | メール送信ログ |
| `apps_system_menu` | `Menu` | メニュー設定 |
| `apps_system_parameter` | `Parameter` | パラメータ設定 |

### django-allauth関連テーブル（6テーブル）

| テーブル名 | 説明 |
| --- | --- |
| `account_emailaddress` | メールアドレス管理 |
| `account_emailconfirmation` | メールアドレス確認 |
| `socialaccount_socialaccount` | ソーシャルアカウント |
| `socialaccount_socialapp` | ソーシャルアプリ設定 |
| `socialaccount_socialapp_sites` | ソーシャルアプリとサイトの関連 |
| `socialaccount_socialtoken` | ソーシャルアカウントトークン |

### Django標準・その他テーブル（11テーブル）

| テーブル名 | 説明 |
| --- | --- |
| `accounts_myuser_groups` | ユーザーとグループの関連 |
| `accounts_myuser_user_permissions` | ユーザーと権限の関連 |
| `auth_group` | グループ |
| `auth_group_permissions` | グループと権限の関連 |
| `auth_permission` | 権限 |
| `django_admin_log` | 管理画面操作ログ |
| `django_content_type` | コンテンツタイプ |
| `django_migrations` | マイグレーション履歴 |
| `django_session` | セッション |
| `django_site` | サイト設定 |
| `sqlite_sequence` | SQLiteシーケンス管理 |

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

## 接続管理機能

### スタッフ・クライアント接続システム
このアプリケーションでは、スタッフとクライアント担当者との接続申請・承認機能を提供しています：

- **接続申請**: スタッフ詳細・クライアント担当者詳細画面から接続依頼を送信
- **メールベース認証**: メールアドレスを基準とした接続管理
- **権限自動付与**: 接続申請時・アカウント作成時の自動権限付与
- **承認管理**: 接続対象者による承認・未承認の切り替え
- **統合管理画面**: スタッフ接続・クライアント接続の統合管理

### 接続フロー
1. **申請作成**: 管理者がスタッフ/クライアント担当者詳細画面で接続依頼を作成
2. **権限付与**: 既存ユーザーがいる場合は自動で権限付与
3. **承認処理**: 対象者がログイン後、接続管理画面で承認・未承認を選択
4. **アカウント作成時**: 新規アカウント作成時に既存申請をチェックして権限付与

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
プロジェクトのテスト構成とルールについては、[テストガイドライン](_docs/testing-guidelines.md)を参照してください。

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
AUTH_USER_MODEL = 'accounts.MyUser'
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
- `/api/master/` - マスター管理API
- `/connect/` - 接続管理（スタッフ・クライアント接続申請）

### 認証
- django-allauthベースの認証
- セッション認証対応

## 🎨 UI/UX

### デザインシステム
- **カラーパレット**: Bootstrap 5準拠
- **タイポグラフィ**: 日本語フォント最適化
- **レスポンシブ**: モバイルファースト設計

### ロジック情報表示システム
- **コーヒーカップアイコン**: ヘッダーのアイコンでページロジック情報の有無を表示
  - `bi-cup`: ロジック情報なし（空のカップ）
  - `bi-cup-hot`: ロジック情報あり（湯気のあるカップ）
- **モーダル表示**: クリックでページ固有のバリデーションロジックを表示
- **カテゴリ分類**: 
  - **単項目チェック**: 個別フィールドのバリデーション
  - **相関チェック**: 複数フィールド間の関連性チェック
  - **自動処理**: システムによる自動変換・取得処理
- **統一デザイン**: カード形式で整理され、影付きで視覚的に区別

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
