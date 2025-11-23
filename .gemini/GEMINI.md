## アプリケーションの概要と特徴

このDjangoアプリケーションは、多機能なWebアプリケーションであり、以下の主要な特徴を持っています。

*   **Djangoフレームワーク**: Python製のWebフレームワークDjangoを基盤としています。
*   **カスタムユーザーモデル**: `apps/accounts/MyUser`を認証に利用しており、柔軟なユーザー管理が可能です。
*   **認証システム**: `django-allauth`を導入し、メールアドレスを主とした認証（サインアップ、ログイン、パスワードリセットなど）を提供しています。
*   **モジュール化された機能**: `api`, `staff`, `client`, `contract`, `company`, `connect`, `common`, `master`, `system`, `accounts`, `home`, `csstest`, `profile`, `kintai`といった複数のDjangoアプリケーションに機能を分割し、高いモジュール性と保守性を実現しています。特に`system`アプリケーションは、`settings`（ドロップダウン、メニュー、パラメータを統合）、`logs`といったサブモジュールに再編され、ユーザー管理機能は独立した`accounts`アプリに移行されました。
*   **国際化対応**: 日本語環境（`ja-JP`）での利用を前提とした設定が施されています。
*   **データ管理機能**: ExcelやPDF形式でのデータ出力機能、管理画面でのインポート/エクスポート機能（`django-import-export`）を備えています。
*   **外部サービス連携**: `gBizINFO`や`zipcloud`などの外部APIとの連携機能を有しています。
*   **ログ記録**: ユーザーのログイン/ログアウトなどのアクションを記録する認証ログ機能を実装しています。
*   **プロフィール管理機能**: スタッフのプロフィール情報 (`StaffProfile`) およびマイナンバー (`StaffProfileMynumber`) の管理機能を提供します。ユーザーモデル (`MyUser`) とプロファイルの姓名は自動的に同期されます。
*   **契約管理機能**: クライアント契約とスタッフ契約の包括的な管理機能を提供し、契約の作成、更新、削除、状況追跡（有効期間中、開始前、期限切れ、無効）が可能です。
*   **勤怠管理機能**: スタッフの日次・月次勤怠管理機能を提供し、労働時間、残業時間、休日労働などの自動計算、および承認ワークフローをサポートします。
*   **接続管理機能**: スタッフ・クライアント担当者との接続申請・承認機能を提供し、メールアドレスベースでの接続依頼、権限の自動付与、承認・未承認の切り替えが可能です。
*   **マスター管理機能**: 資格・スキル、銀行・支店、支払条件など、多岐にわたるマスターデータを管理します。すべてのマスタはカテゴリ別に整理され、統一されたリスト画面から各々の管理ページへ効率的にアクセスできる構造になっています。
*   **統一変更履歴システム**: `AppLog`モデルを使用して、スタッフ、クライアント、契約などすべてのデータ変更を統一的に追跡・表示する仕組みを実装しています。各詳細画面で変更履歴を確認でき、操作者・日時・変更内容を記録します。

## 📁 プロジェクト構造

```
django-study-base/
├── _docs/                  # ドキュメント
├── _sample_data/           # サンプルデータ
├── _scripts/               # 管理・運用スクリプト
│
├── apps/                   # Djangoアプリケーション
│   ├── system/             # システム管理
│   │   ├── logs/           # ログ管理 (アプリログ、メールログ)
│   │   └── settings/       # 設定管理 (ドロップダウン、メニュー、パラメータ)
│   ├── accounts/           # ユーザー管理・認証
│   ├── profile/            # プロフィール管理
│   ├── master/             # マスター管理 (資格、スキル、銀行、支払条件)
│   ├── staff/              # スタッフ管理
│   ├── client/             # クライアント管理
│   ├── contract/           # 契約管理
│   ├── kintai/             # 勤怠管理
│   ├── company/            # 会社・部署管理
│   ├── connect/            # 接続管理 (スタッフ・クライアント接続申請)
│   ├── common/             # 共通機能
│   ├── home/               # ホームページ
│   ├── csstest/            # CSSテスト・開発
│   └── api/                # REST API
├── config/                 # プロジェクト設定
├── media/                  # アップロードされたファイル
│   ├── client_files/       # クライアントアップロードファイル
│   │   └── {クライアントID}/
│   └── staff_files/        # スタッフアップロードファイル
│       └── {スタッフID}/
├── statics/                # 静的ファイル
├── templates/              # HTMLテンプレート
└── requirements.txt        # 依存関係
```

## データベーステーブル一覧

### 本アプリケーション独自テーブル

| テーブル名 | 説明 |
| --- | --- |
| `accounts_myuser` | カスタムユーザー（メインテーブル） |
| `accounts_myuser_groups` | ユーザーとグループの関連 |
| `accounts_myuser_user_permissions` | ユーザーと権限の関連 |
| `apps_client` | クライアント基本情報 |
| `apps_client_contacted` | クライアント連絡履歴 |
| `apps_client_department` | クライアント部署情報 |
| `apps_client_file` | クライアントファイル |
| `apps_client_user` | クライアント担当者 |
| `apps_company` | 会社情報 |
| `apps_company_department` | 部署情報 |
| `apps_company_user` | 会社担当者 |
| `apps_connect_bank_request` | 銀行口座変更申請 |
| `apps_connect_client` | クライアント接続申請 |
| `apps_connect_contact_request` | 連絡先変更申請 |
| `apps_connect_disability_request` | 障害者情報変更申請 |
| `apps_connect_international_request` | 国際情報変更申請 |
| `apps_connect_mynumber_request` | マイナンバー接続申請 |
| `apps_connect_profile_request` | プロフィール変更申請 |
| `apps_connect_staff` | スタッフ接続申請 |
| `apps_contract_client` | クライアント契約 |
| `apps_contract_staff` | スタッフ契約 |
| `apps_kintai_staff_timesheet` | 月次勤怠 |
| `apps_kintai_staff_timecard` | 日次勤怠 |
| `apps_master_bank` | 銀行マスター |
| `apps_master_bank_branch` | 銀行支店マスター |
| `apps_master_bill_bank` | 会社銀行マスター |
| `apps_master_bill_payment` | 支払条件マスター |
| `apps_master_information` | お知らせマスター |
| `apps_master_information_file` | お知らせファイル |
| `apps_master_qualification` | 資格マスター（カテゴリと資格） |
| `apps_master_skill` | 技能マスター（カテゴリと技能） |
| `apps_profile_staff` | スタッフプロフィール |
| `apps_profile_staff_bank` | プロフィール銀行口座 |
| `apps_profile_staff_contact` | プロフィール連絡先 |
| `apps_profile_staff_disability` | プロフィール障害者情報 |
| `apps_profile_staff_international` | プロフィール外国籍情報 |
| `apps_profile_staff_mynumber` | プロフィールマイナンバー |
| `apps_profile_staff_qualification` | プロフィール保有資格 |
| `apps_profile_staff_skill` | プロフィール保有スキル |
| `apps_staff` | スタッフ基本情報 |
| `apps_staff_bank` | スタッフ銀行口座 |
| `apps_staff_contacted` | スタッフ連絡履歴 |
| `apps_staff_contact` | スタッフ連絡先 |
| `apps_staff_disability` | スタッフ障害者情報 |
| `apps_staff_file` | スタッフファイル |
| `apps_staff_international` | スタッフ外国籍情報 |
| `apps_staff_mynumber` | スタッフマイナンバー |
| `apps_staff_qualification` | スタッフ保有資格 |
| `apps_staff_skill` | スタッフ保有スキル |
| `apps_system_app_log` | アプリケーション操作ログ |
| `apps_system_dropdowns` | ドロップダウン設定 |
| `apps_system_mail_log` | メール送信ログ |
| `apps_system_menu` | メニュー設定 |
| `apps_system_parameter` | パラメータ設定 |

### django-allauth関連テーブル

| テーブル名 | 説明 |
| --- | --- |
| `account_emailaddress` | メールアドレス管理 |
| `account_emailconfirmation` | メールアドレス確認 |
| `socialaccount_socialaccount` | ソーシャルアカウント |
| `socialaccount_socialapp` | ソーシャルアプリ設定 |
| `socialaccount_socialapp_sites` | ソーシャルアプリとサイトの関連 |
| `socialaccount_socialtoken` | ソーシャルアカウントトークン |

### Django標準・その他テーブル

| テーブル名 | 説明 |
| --- | --- |
| `auth_group` | グループ |
| `auth_group_permissions` | グループと権限の関連 |
| `auth_permission` | 権限 |
| `django_admin_log` | 管理画面操作ログ |
| `django_content_type` | コンテンツタイプ |
| `django_migrations` | マイグレーション履歴 |
| `django_session` | セッション |
| `django_site` | サイト設定 |
| `sqlite_sequence`| シーケンス |

## 開発方針

既存の指針に加え、以下の点を重視して開発を進めます。

*   **シンプルで保守性の高いコード**: ソースコードは常にシンプルさを追求し、長期的な保守性を確保します。
*   **堅牢なセキュリティ**: ユーザー認証、データ保護、アクセス制御など、アプリケーション全体のセキュリティを最優先します。
*   **既存ライブラリの積極的な活用**: `django-allauth`や`python-stdnum==2.1`、その他の信頼性の高いミドルウェア、ライブラリを積極的に活用し、独自実装を最小限に抑えることで、開発効率と品質を向上させます。
*   **テストによる品質保証**: 作成された機能は、適切なテスト（単体テスト、結合テストなど）によって品質が保証されるようにします。

### 開発プロセスにおける追加の指針

*   **コミュニケーション言語**: エージェントとのやり取りは日本語で行う。

*   **home.htmlのMiddleware欄に、利用しているコンポーネントを記載する。**
    **新しいライブラリを追加した場合は、必ずこの欄に追記すること。**
*   **プログラムを追加した場合には、テストケースを追加し、テストケースが通るようにする。**
*   **テストケースが完了するまで修正を行う。時間がかかっている場合には一度方針について確認を行う。**
*   **テストケースが長い場合には修正する前にファイルを分割して実行しやすいようにする。修正は分割した後。**
*   **画面に表示する日時は `YYYY/MM/DD HH:MM:SS` の形式に統一する。**
*   **変更履歴の統一**: すべてのモデルで`AppLog`を使用した統一的な変更履歴管理を行う。詳細画面には必ず変更履歴セクションを追加し、同じ形式で表示する。
*   **CHANGELOG.mdの更新**: 変更履歴は`CHANGELOG.md`に記録する。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングに従う。各変更は「Added」「Changed」「Removed」のいずれかのセクションに分類し、簡潔かつ具体的に記述する。
