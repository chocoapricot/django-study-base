# プロジェクト構成

このドキュメントは、プロジェクトの構成、特に `apps`、`templates`、`config` ディレクトリに焦点を当てて概説します。

## `apps/`

このディレクトリには、プロジェクトを構成する様々なDjangoアプリケーションが含まれています。

### `accounts/`
- **`models.py`**: ユーザー関連モデル。
  - `MyUser`: 標準のUserモデルを拡張したカスタムユーザーモデル。StaffProfileとの連携で、姓・名の同期機能を持つ。
- **`signals.py`**: ユーザーモデルに関するシグナル。
  - `check_connection_requests_on_user_creation`: ユーザー作成時に接続申請をチェックし、権限を付与します。
- **`validators.py`**: カスタムバリデーション。
  - `MyPasswordValidator`: パスワードの複雑性（長さ、記号の有無）を検証するカスタムバリデータ。
- **`views.py`**: ユーザー認証（ログイン、ログアウト）、登録、プロフィール表示を処理します。
- **`forms.py`**: ユーザー登録およびプロフィール編集用のフォーム。
- **`urls.py`**: accountsアプリケーションのURLルーティング。
- **`admin.py`**: アカウントモデルのDjango管理インターフェース設定。

### `api/`
- **`helpers.py`**: 外部APIとの連携用ヘルパー。
  - `fetch_company_info(corporate_number)`: 法人番号からgBizINFOのAPIを呼び出し、企業情報を取得します。
  - `fetch_zipcode(zipcode)`: 郵便番号から住所情報を取得するAPIを呼び出します。
- **`views.py`**: APIリクエストを処理するビュー。
- **`urls.py`**: APIエンドポイントのURLルーティング。

### `client/`
- **`models.py`**: クライアント関連モデル。
  - `Client`: 取引先企業（クライアント）の基本情報を管理するモデル。
  - `ClientDepartment`: クライアント企業内の組織（部署）情報を管理するモデル。
  - `ClientUser`: クライアント企業の担当者情報を管理するモデル。
  - `ClientContacted`: クライアント企業への連絡履歴を管理するモデル。
  - `ClientFile`: クライアントに関連する添付ファイルを管理するモデル。
- **`signals.py`**: クライアント関連モデルのシグナル。
  - `log_client_file_save`: `ClientFile`の作成・更新をログに記録します。
  - `log_client_file_delete`: `ClientFile`の削除をログに記録します。
- **`views.py`**: クライアント、部署、ユーザー、連絡履歴を管理するためのビュー。
- **`forms.py`**: クライアント関連データを作成・編集するためのフォーム。
- **`urls.py`**: clientアプリケーションのURLルーティング。

### `common/`
- **`models.py`**: 共通モデル。
  - `MyModel`: プロジェクト共通の抽象ベースモデル。バージョン管理、作成・更新日時、作成・更新者を自動で記録する。
- **`authlog.py`**: 認証関連のログを記録します。
  - `get_client_ip`: リクエストからクライアントIPを取得します。
  - `log_user_login`: ユーザーのログインイベントをログに記録します。
  - `log_user_logout`: ユーザーのログアウトイベントをログに記録します。
- **`backends.py`**: カスタム認証バックエンド。
  - `MyPasswordRules`: ユーザー名/Emailとパスワードで認証し、アクティブ状態も確認します。
- **`signals.py`**: 汎用的なモデル変更ログ記録シグナル。
  - `log_pre_save`: モデル保存前に変更差分を計算します。
  - `log_save`: モデル保存後に作成・更新ログを記録します。
  - `log_delete`: モデル削除後に削除ログを記録します。
- **`utils.py`**: 汎用的なユーティリティ関数。
  - `fill_excel_from_template`: Excelテンプレートにデータを差し込みます。
  - `fill_pdf_from_template`: PDFフォームテンプレートにデータを差し込みます。

### `company/`
- **`models.py`**: 社内組織構造のモデル。
  - `CompanyDepartment`: 自社の部署情報を管理するモデル。部署コードと有効期間に基づいた重複チェック機能を持つ。
  - `Company`: 自社の会社情報を管理するモデル。通常、このテーブルには1つのレコードのみが存在する。
- **`views.py`**: 会社情報と部署を管理するためのビュー。
- **`forms.py`**: 会社および部署データ用のフォーム。
- **`urls.py`**: companyアプリケーションのURLルーティング。

### `connect/`
- **`models.py`**: スタッフとクライアントを接続するためのモデル。
  - `ConnectStaff`: 外部のスタッフがシステムにアクセスするための接続申請を管理するモデル。
  - `ConnectClient`: 外部のクライアント担当者がシステムにアクセスするための接続申請を管理するモデル（将来拡張用）。
- **`utils.py`**: 権限管理ユーティリティ。
  - `grant_profile_permissions`: プロフィール関連権限を付与します。
  - `grant_connect_permissions`: スタッフ接続関連権限を付与します。
  - `check_and_grant_permissions_for_email`: メールアドレスを元にスタッフ接続申請をチェックし権限付与します。
  - `grant_client_connect_permissions`: クライアント接続関連権限を付与します。
  - `check_and_grant_client_permissions_for_email`: メールアドレスを元にクライアント接続申請をチェックし権限付与します。
- **`templatetags/connect_tags.py`**: テンプレートタグ。
  - `get_item`: 辞書からキーで値を取得します。
- **`views.py`**: 接続リクエストを処理するためのビュー。
- **`urls.py`**: connectアプリケーションのURLルーティング。

### `contract/`
- **`models.py`**: 契約関連モデル。
  - `ClientContract`: クライアント（取引先企業）との契約情報を管理するモデル。
  - `StaffContract`: スタッフ（従業員・フリーランス等）との契約情報を管理するモデル。
- **`views.py`**: クライアントおよびスタッフの契約を管理するためのビュー。
- **`forms.py`**: 契約データ用のフォーム。
- **`urls.py`**: contractアプリケーションのURLルーティング。

### `master/`
- **`models.py`**: マスターデータモデル。
  - `Qualification`: 資格情報を管理するマスターデータモデル（階層構造対応）。
  - `Skill`: 技能（スキル）情報を管理するマスターデータモデル（階層構造対応）。
  - `BillPayment`: 支払条件（締め日・支払日など）を管理するマスターデータモデル。
  - `BillBank`: 自社の振込先銀行口座情報を管理するマスターデータモデル。
  - `Bank`: 銀行情報を管理するマスターデータモデル。
  - `BankBranch`: 銀行の支店情報を管理するマスターデータモデル。
- **`signals.py`**: (空) 共通シグナルを使用。

### `profile/`
- **`models.py`**: スタッフプロフィール関連モデル。
  - `StaffProfile`: スタッフ（ユーザー）のプロフィール情報を管理するモデル。
  - `StaffProfileQualification`: スタッフが保有する資格情報を管理するモデル。
  - `StaffProfileSkill`: スタッフが保有する技能（スキル）情報を管理するモデル。
  - `ProfileMynumber`: スタッフのマイナンバー情報を管理するモデル。

### `staff/`
- **`models.py`**: スタッフメンバー関連モデル。
  - `Staff`: スタッフ（従業員、契約社員など）の基本情報を管理するモデル。
  - `StaffFile`: スタッフに関連する添付ファイルを管理するモデル。
  - `StaffContacted`: スタッフへの連絡履歴を管理するモデル。
  - `StaffQualification`: スタッフが保有する資格情報を管理するモデル（中間テーブル）。
  - `StaffSkill`: スタッフが保有する技能（スキル）情報を管理するモデル（中間テーブル）。
- **`signals.py`**: スタッフ関連モデルの変更ログ用シグナル。
  - `log_staff_qualification_save`, `log_staff_qualification_delete`
  - `log_staff_skill_save`, `log_staff_skill_delete`
  - `log_staff_file_save`, `log_staff_file_delete`

### `system/`
- **`logs/`**
  - **`models.py`**:
    - `MailLog`: システムから送信されるメールのログを管理するモデル。
    - `AppLog`: アプリケーション内での主要な操作のログを管理するモデル。
  - **`signals.py`**: ログ関連シグナル。
    - `log_signup_email`: ユーザー登録時のメール送信をログ記録します。
  - **`utils.py`**: ログ関連ユーティリティ。
    - `log_mail`: メール送信ログを作成します。
    - `update_mail_log_status`: メールログのステータスを更新します。
    - `log_model_action`: モデル操作の汎用ログ記録関数。
- **`settings/`**
  - **`models.py`**:
    - `Dropdowns`: アプリケーション全体で使用されるドロップダウンリストの選択肢を管理するモデル。
    - `Parameter`: アプリケーション全体で使用される設定値を管理するモデル。
    - `Menu`: ナビゲーションメニューの項目を管理するモデル。
  - **`context_processors.py`**:
    - `menu_items`: メニュー項目をテンプレートコンテキストに追加します。
  - **`utils.py`**:
    - `my_parameter`: `Parameter`モデルからキーで設定値を取得します。
  - **`templatetags/`**:
    - **`dropdowns.py`**: `my_name`: `Dropdowns`モデルから表示名を取得します。
    - **`help_tags.py`**: `my_help_icon`, `my_help_preset`: ヘルプアイコンとツールチップを表示します。
    - **`menus.py`**: `my_menu_active`, `has_menu_permission`: メニューのアクティブ状態と権限をチェックします。
    - **`parameters.py`**: `parameter`: `Parameter`モデルから設定値を取得します。

## `templates/`

このディレクトリには、プロジェクトのHTMLテンプレートがアプリケーションごとに整理されて格納されています。

### `account/`
- `_account_base.html`: アカウント関連ページの基本レイアウト。
- `email_confirm.html`: メールアドレス確認ページ。
- `email_confirmed.html`: メールアドレス確認完了ページ。
- `email_verification_sent.html`: メールアドレス確認メール送信完了ページ。
- `login.html`: ログインページ。
- `password_reset.html`: パスワードリセット要求ページ。
- `password_reset_done.html`: パスワードリセット要求完了ページ。
- `password_reset_from_key.html`: 新しいパスワードを設定するページ。
- `password_reset_from_key_done.html`: パスワードリセット完了ページ。
- `profile.html`: ユーザープロフィール表示ページ。
- `signup.html`: ユーザー登録ページ。
- `terms_of_service.html`: 利用規約ページ。
- `verification_sent.html`: 認証メール送信完了ページ。
- `email/password_reset_key_message.txt`: パスワードリセットメールの本文。
- `email/password_reset_key_subject.txt`: パスワードリセットメールの件名。

### `client/`
- `_client_info_card.html`: クライアントの基本情報を表示するカードコンポーネント。
- `client_change_history_list.html`: クライアント情報の変更履歴一覧ページ。
- `client_confirm_delete.html`: クライアント削除の確認ページ。
- `client_contacted_confirm_delete.html`: クライアント連絡履歴削除の確認ページ。
- `client_contacted_detail.html`: クライアント連絡履歴の詳細ページ。
- `client_contacted_form.html`: クライアント連絡履歴の作成・編集フォームページ。
- `client_contacted_list.html`: クライアント連絡履歴の一覧ページ。
- `client_department_confirm_delete.html`: クライアント部署削除の確認ページ。
- `client_department_form.html`: クライアント部署の作成・編集フォームページ。
- `client_department_list.html`: クライアント部署の一覧ページ。
- `client_detail.html`: クライアント詳細ページ。
- `client_file_confirm_delete.html`: クライアント添付ファイル削除の確認ページ。
- `client_file_form.html`: クライアント添付ファイルのアップロードフォームページ。
- `client_file_list.html`: クライアント添付ファイルの一覧ページ。
- `client_form.html`: クライアントの作成・編集フォームページ。
- `client_list.html`: クライアント一覧ページ。
- `client_user_confirm_delete.html`: クライアント担当者削除の確認ページ。
- `client_user_detail.html`: クライアント担当者の詳細ページ。
- `client_user_form.html`: クライアント担当者の作成・編集フォームページ。
- `client_user_list.html`: クライアント担当者の一覧ページ。
- `client_user_mail_send.html`: クライアント担当者へのメール送信ページ。

### `common/`
- `_base.html`: 全てのページの基礎となるベーステンプレート。
- `_change_history_list.html`: 変更履歴を表示するための共通コンポーネント。
- `simplex_list.html`: シンプルなリスト表示用の共通テンプレート。

### `company/`
- `_department_list_table.html`: 部署一覧を表示するテーブルコンポーネント。
- `company_change_history_list.html`: 会社情報の変更履歴一覧ページ。
- `company_detail.html`: 会社情報の詳細ページ。
- `company_edit.html`: 会社情報の編集ページ。
- `department_confirm_delete.html`: 部署削除の確認ページ。
- `department_detail.html`: 部署の詳細ページ。
- `department_form.html`: 部署の作成・編集フォームページ。

### `connect/`
- `client_list.html`: クライアント接続申請の一覧ページ。
- `index.html`: 接続申請のトップページ。
- `staff_list.html`: スタッフ接続申請の一覧ページ。

### `contract/`
- `client_contract_delete.html`: クライアント契約削除の確認ページ。
- `client_contract_detail.html`: クライアント契約の詳細ページ。
- `client_contract_form.html`: クライアント契約の作成・編集フォームページ。
- `client_contract_list.html`: クライアント契約の一覧ページ。
- `client_select.html`: 契約対象クライアントの選択ページ。
- `contract_change_history_list.html`: 契約情報の変更履歴一覧ページ。
- `contract_index.html`: 契約管理のトップページ。
- `staff_contract_delete.html`: スタッフ契約削除の確認ページ。
- `staff_contract_detail.html`: スタッフ契約の詳細ページ。
- `staff_contract_form.html`: スタッフ契約の作成・編集フォームページ。
- `staff_contract_list.html`: スタッフ契約の一覧ページ。
- `staff_select.html`: 契約対象スタッフの選択ページ。

### `home/`
- `home.html`: ログイン後のホームページ/ダッシュボード。

### `logs/`
- `app_log_list.html`: アプリケーション操作ログの一覧ページ。
- `mail_log_detail.html`: メール送信ログの詳細ページ。
- `mail_log_list.html`: メール送信ログの一覧ページ。

### `master/`
- `_bank_info.html`: 銀行情報の詳細表示コンポーネント。
- `_bank_info_simple.html`: 銀行情報の簡易表示コンポーネント。
- `bank_branch_delete.html`: 銀行支店削除の確認ページ。
- `bank_branch_form.html`: 銀行支店の作成・編集フォームページ。
- `bank_delete.html`: 銀行削除の確認ページ。
- `bank_form.html`: 銀行の作成・編集フォームページ。
- `bank_management.html`: 銀行・支店管理ページ。
- `bill_bank_delete.html`: 振込先銀行削除の確認ページ。
- `bill_bank_form.html`: 振込先銀行の作成・編集フォームページ。
- `bill_bank_list.html`: 振込先銀行の一覧ページ。
- `bill_payment_delete.html`: 支払条件削除の確認ページ。
- `bill_payment_form.html`: 支払条件の作成・編集フォームページ。
- `bill_payment_list.html`: 支払条件の一覧ページ。
- `master_change_history_list.html`: マスターデータの変更履歴一覧ページ。
- `master_index_list.html`: マスターデータ管理のトップページ。
- `qualification_category_form.html`: 資格カテゴリの作成・編集フォームページ。
- `qualification_delete.html`: 資格削除の確認ページ。
- `qualification_detail.html`: 資格の詳細ページ。
- `qualification_form.html`: 資格の作成・編集フォームページ。
- `qualification_list.html`: 資格の一覧ページ。
- `skill_category_form.html`: スキルカテゴリの作成・編集フォームページ。
- `skill_delete.html`: スキル削除の確認ページ。
- `skill_detail.html`: スキルの詳細ページ。
- `skill_form.html`: スキルの作成・編集フォームページ。
- `skill_list.html`: スキルの一覧ページ。

### `profile/`
- `mynumber_delete.html`: マイナンバー情報削除の確認ページ。
- `mynumber_detail.html`: マイナンバー情報の詳細ページ。
- `mynumber_form.html`: マイナンバー情報の作成・編集フォームページ。
- `profile_delete.html`: プロフィール削除の確認ページ。
- `profile_detail.html`: プロフィールの詳細ページ。
- `profile_form.html`: プロフィールの作成・編集フォームページ。
- `profile_qualification_delete.html`: プロフィール資格削除の確認ページ。
- `profile_qualification_form.html`: プロフィール資格の作成・編集フォームページ。
- `profile_qualification_list.html`: プロフィール資格の一覧ページ。
- `profile_skill_delete.html`: プロフィールスキル削除の確認ページ。
- `profile_skill_form.html`: プロフィールスキルの作成・編集フォームページ。
- `profile_skill_list.html`: プロフィールスキルの一覧ページ。

### `staff/`
- `_staff_info_card.html`: スタッフの基本情報を表示するカードコンポーネント。
- `staff_change_history_list.html`: スタッフ情報の変更履歴一覧ページ。
- `staff_confirm_delete.html`: スタッフ削除の確認ページ。
- `staff_contacted_confirm_delete.html`: スタッフ連絡履歴削除の確認ページ。
- `staff_contacted_detail.html`: スタッフ連絡履歴の詳細ページ。
- `staff_contacted_form.html`: スタッフ連絡履歴の作成・編集フォームページ。
- `staff_contacted_list.html`: スタッフ連絡履歴の一覧ページ。
- `staff_detail.html`: スタッフ詳細ページ。
- `staff_file_confirm_delete.html`: スタッフ添付ファイル削除の確認ページ。
- `staff_file_form.html`: スタッフ添付ファイルのアップロードフォームページ。
- `staff_file_list.html`: スタッフ添付ファイルの一覧ページ。
- `staff_form.html`: スタッフの作成・編集フォームページ。
- `staff_list.html`: スタッフ一覧ページ。
- `staff_mail_send.html`: スタッフへのメール送信ページ。
- `staff_qualification_confirm_delete.html`: スタッフ資格削除の確認ページ。
- `staff_qualification_delete.html`: スタッフ資格削除の確認ページ。
- `staff_qualification_detail.html`: スタッフ資格の詳細ページ。
- `staff_qualification_form.html`: スタッフ資格の作成・編集フォームページ。
- `staff_qualification_list.html`: スタッフ資格の一覧ページ。
- `staff_skill_confirm_delete.html`: スタッフスキル削除の確認ページ。
- `staff_skill_delete.html`: スタッフスキル削除の確認ページ。
- `staff_skill_detail.html`: スタッフスキルの詳細ページ。
- `staff_skill_form.html`: スタッフスキルの作成・編集フォームページ。
- `staff_skill_list.html`: スタッフスキルの一覧ページ。

## `config/`

このディレクトリには、Djangoプロジェクトの主要な設定が含まれています。

- **`settings/`**: このディレクトリにはプロジェクトの設定が含まれています。
  - **`settings.py`**: 主要な設定ファイルで、インストール済みアプリ、ミドルウェア、データベース設定などを定義します。`django-allauth`の設定も含まれています。
  - **`develop.py`**, **`product.py`**, **`test.py`**: 環境別の設定。
- **`urls.py`**: ルートURL設定ファイル。`apps/`ディレクトリ内のすべてのアプリケーションからのURLパターンをインクルードします。
- **`wsgi.py`** and **`asgi.py`**: WSGIおよびASGI互換ウェブサーバーのエントリポイント。
