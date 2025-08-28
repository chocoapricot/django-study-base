# AGENTS_ja.md

このファイルは、このコードベースで作業するAIエージェント向けのガイダンスを提供します。

## プロジェクト概要

これは「django-study-base」と呼ばれるDjangoベースのWebアプリケーションで、以下の主要機能を持つビジネス管理システムです：

- **スタッフ管理**: 従業員データの管理と追跡
- **クライアント管理**: 顧客関係管理機能
- **契約管理**: クライアント契約・スタッフ契約の管理と追跡
- **会社・部署管理**: 会社情報と部署の体系的管理
- **接続管理**: スタッフ・クライアント担当者との接続申請・承認機能
- **プロフィール管理**: ユーザープロファイル、マイナンバー管理
- **マスター管理**: 資格、スキル、銀行・支店、支払条件などのマスターデータ管理
- **システム管理**: ユーザー管理、メニュー、パラメータ、ドロップダウン設定
- **APIレイヤー**: データアクセス用RESTful APIエンドポイント
- **認証**: ロールベースアクセス付きカスタムユーザー認証

このアプリケーションは日本のユーザー向けに設計されており（ja-JPロケール、Asia/Tokyoタイムゾーン）、ビジネスワークフロー用のデータインポート/エクスポート、PDF生成、Excel統合機能を含んでいます。

### 主要なビジネス領域
- スタッフ管理と連絡先追跡、資格・スキル管理
- クライアント関係管理、部署・担当者管理
- 契約管理（クライアント契約・スタッフ契約の作成、更新、削除、状況追跡）
- 会社・部署管理（法人番号検索、郵便番号検索、変更履歴追跡）
- 接続管理（スタッフ・クライアント担当者との接続申請・承認、権限自動付与）
- プロフィール管理 (`StaffProfile`, `StaffProfileMynumber`)
- マスターデータ管理（資格、スキル、銀行・支店、支払条件、会社銀行）
- システム設定（ドロップダウン、メニュー、パラメータ）とユーザー管理、ログ管理
- **統一変更履歴管理**: AppLogシステムによる全データの変更追跡と表示
- 共通ユーティリティと共有機能
- UI開発用CSSテスト環境

### 変更履歴管理の特徴
- **統一されたアプローチ**: 全モデル（スタッフ、クライアント、契約等）で同じ履歴管理システムを使用
- **詳細画面統合**: 各エンティティの詳細画面に変更履歴セクションを標準装備
- **操作追跡**: 作成・更新・削除操作を自動記録し、操作者と日時を保存
- **視覚的表示**: バッジとテーブルを使った直感的な履歴表示

## ビルドとテストのコマンド

開発環境をセットアップしてアプリケーションを実行するには、次のコマンドを使用します。

- **依存関係のインストール:**
  ```bash
  pip install -r requirements.txt
  ```

- **テストの実行:**
  ```bash
  python manage.py test
  ```

- **開発サーバーの実行:**
  ```bash
  python manage.py runserver
  ```

## コードスタイルガイドライン

## 改行コード統一ルール
- **Windows環境**: すべてのファイルでCRLF（\r\n）を使用
- **Git設定**: `git config core.autocrlf true` を設定済み
- **対象ファイル**: Python、HTML、CSS、JavaScript、Markdown、設定ファイルすべて
- **理由**: Windows環境での一貫性とGitワーニング回避

## HTML/テンプレート編集方針
- **改行制限**: 200文字程度まで改行しない
- **コメント保持**: 既存のコメントを勝手に削除しない
- **フォーマット保持**: 元のファイルの改行構造を保持する
- **最小限修正**: 必要最小限の修正のみを行う

## ファイル編集の基本原則
1. 元のフォーマットを尊重する
2. 不要な改行や空白の変更を避ける
3. コメントや説明文を保持する
4. 機能的な修正のみに集中する
5. 改行コードはCRLFで統一する

## テンプレートファイル（HTML）
- 長い属性リストでも200文字以内なら1行で記述
- 既存のインデントレベルを維持
- コメント（<!-- -->）を保持
- 不要な空行を追加しない

## Bootstrapボタンのスタイル統一
- **必須ルール**: すべてのボタンに `btn-sm` クラスを追加する
- **例**: `class="btn btn-sm btn-primary"`, `class="btn btn-sm btn-secondary"`
- **対象**: フォームボタン、リンクボタン、操作ボタンすべて
- **例外**: 特別な理由がある場合のみ例外を認める

## 戻るボタンの配置ルール
- **基本原則**: 戻るボタンはコンテンツ内の左下に配置する
- **禁止**: カードフッター（card-footer）での戻るボタン配置は禁止
- **card-footer使用可能**: 「全て表示」などの補助リンクは card-footer 使用可
- **推奨レイアウト**: 
  ```html
  <div class="row mt-3">
      <div class="col text-left">
          <a href="..." class="btn btn-sm btn-secondary">戻る</a>
      </div>
  </div>
  ```
- **参考**: クライアント変更履歴一覧のレイアウトに準拠

## フォームデザインの統一ルール
- **ラベル配置**: `col-form-label` + `text-align:right` で右寄せ
- **ラベルスタイル**: 太字（`<strong>`）は使用しない、通常の文字重量
- **入力欄サイズ**: すべての入力欄に `form-control-sm` クラスを追加
- **ボタン分離**: API呼び出しボタンは入力欄と分離して独立したカラムに配置
- **推奨レイアウト**:
  ```html
  <div class="row mb-3 align-items-center">
      <label for="..." class="col-sm-2 col-form-label" style="text-align:right">ラベル</label>
      <div class="col-sm-4">
          <input class="form-control form-control-sm" ...>
      </div>
      <div class="col-sm">
          <button type="button" class="btn btn-sm btn-secondary">ボタン</button>
      </div>
  </div>
  ```
- **参考**: クライアントフォームのレイアウトに準拠

## Tooltipの統一ルール
- **テンプレートタグ使用**: カスタムテンプレートタグ `{% load help_tags %}` を使用（_base.htmlで自動読み込み済み）
- **基本使用方法**:
  ```html
  <!-- プリセットヘルプテキスト使用 -->
  <label>ラベル名 {% my_help_preset "corporate_number" %}</label>
  
  <!-- カスタムヘルプテキスト使用 -->
  <label>ラベル名 {% my_help_icon "カスタム説明文" %}</label>
  
  <!-- 配置指定（デフォルトはtop） -->
  {% my_help_preset "postal_code" "right" %}
  ```
- **利用可能なプリセット**:
  - `corporate_number`: 半角数字13桁ハイフンなし
  - `postal_code`: 半角数字7桁ハイフンなし
  - `gbiz_api`: 経産省のgBizINFO-APIで取得
  - `postal_api`: フリーの郵便番号APIで取得
  - `staff_selection`: 社員番号・入社日が登録されているスタッフのみ選択可能
  - `client_selection`: 基本契約締結日が登録されているクライアントのみ選択可能
  - `hire_date`: 入社日登録しないと契約登録不可
  - `employee_no`: 半角英数字10文字まで（空欄可）、社員番号登録しないと契約登録不可
  - `bank_code`: 4桁の数字で入力（任意）
  - `branch_code`: 3桁の数字で入力（任意）
  - `account_number`: 1-8桁の数字で入力
  - その他多数（`apps/common/templatetags/help_tags.py`のHELP_TEXTSを参照）
- **新しいプリセット追加**: `apps/common/templatetags/help_tags.py`のHELP_TEXTS辞書に追加
- **従来の直接記述は非推奨**: 新しいテンプレートタグを使用してください

## 削除ボタンの統一ルール
- **すべての削除ボタン**: `btn-dark` を使用して統一
- **対象**:
  - 詳細画面の削除ボタン
  - 一覧画面のアイコン削除ボタン
  - 削除確認画面の実行ボタン
- **理由**: 
  - プロジェクト全体での視覚的統一性を重視
  - `btn-danger` は緊急性の高いエラーやアラート用に予約
- **推奨実装**:
  ```html
  <!-- 詳細画面 -->
  <a href="..." class="btn btn-sm btn-dark">削除</a>
  
  <!-- 削除確認画面 -->
  <button type="submit" class="btn btn-sm btn-dark">削除する</button>
  
  <!-- 一覧画面のアイコン -->
  <a href="..." class="btn btn-dark btn-sm" title="削除">
      <i class="bi bi-x"></i>
  </a>
  ```

## 削除確認画面のアラートメッセージルール
- **必須要素**: すべての削除確認画面に警告アラートを表示
- **アラートクラス**: `alert alert-warning` を使用
- **アイコン**: `bi-exclamation-triangle-fill` を使用
- **メッセージ**: 「この操作は取り消せません。」を必ず含める
- **推奨実装**:
  ```html
  <div class="alert alert-warning" role="alert">
      <i class="bi bi-exclamation-triangle-fill"></i>
      [対象]を削除しますか？この操作は取り消せません。
  </div>
  ```
- **配置**: カードボディの最初に配置
- **目的**: ユーザーに削除操作の重要性と不可逆性を明確に伝える

## フォームウィジェットの統一ルール
- **必須クラス**: すべてのフォーム入力欄に `form-control form-control-sm` を適用
- **テキスト入力**: `forms.TextInput(attrs={'class': 'form-control form-control-sm'})`
- **テキストエリア**: `forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3})`
- **URL入力**: `forms.URLInput(attrs={'class': 'form-control form-control-sm'})`
- **選択欄**: `forms.Select(attrs={'class': 'form-control form-control-sm'})`

## カラム幅の推奨設定
- **ラベル**: `col-sm-2` (固定)
- **短い入力欄**: `col-sm-3` (郵便番号など)
- **中程度入力欄**: `col-sm-4` (法人番号など)
- **標準入力欄**: `col-sm-6` (名前など)
- **長い入力欄**: `col-sm-8` (URL、メモなど)
- **最大幅入力欄**: `col-sm-10` (住所など)
- **ボタン用**: `col-sm` (残り幅を自動調整)

## Pythonファイル
- PEP 8に準拠
- 日本語コメントを積極的に使用
- docstringは日本語で記述
- 変数名・関数名は英語

## JavaScriptファイル
- 既存のスタイルに合わせる
- コメントは日本語で記述
- 不要な改行を避ける

## CSSファイル
- 既存のフォーマットを維持
- コメントを保持
- プロパティの順序を変更しない
##
 変更履歴表示の統一ルール
- **配置**: 詳細画面の最下部に配置する
- **タイトル**: 「変更履歴」で統一
- **テーブル構造**: 対象・操作・変更内容・変更者・日時の5列構成
- **バッジスタイル**: 
  - 対象: モデル別に色分け（基本情報=primary、資格=info、技能=success、契約情報=primary/success）
  - 操作: 作成=success、編集=warning、削除=danger
- **日時フォーマット**: `Y/m/d H:i:s` 形式で統一
- **データソース**: `AppLog`モデルを使用し、`create`・`update`・`delete`操作のみ表示
- **件数制限**: 最新10件まで表示
- **空状態**: 「変更履歴がありません」メッセージを表示
- **推奨実装**:
  ```html
  <!-- 変更履歴 -->
  <div class="content-box card bg-light mt-2 mb-4" style="max-width: 100%;">
      <div class="card-header d-flex justify-content-between align-items-center">
          変更履歴
      </div>
      <div class="card-body mb-0">
          <table class="table table-hover me-2 mt-2 mb-0" style="border-top: 1px solid #ddd;">
              <!-- テーブル内容 -->
          </table>
      </div>
  </div>
  ```
## テスト手順

pytestでは実行できないので、python manage.py testコマンドを利用してください。

## テストファイル構成ルール

### 基本原則
- **テストは必ず`tests/`ディレクトリ内に配置する**
- 単一ファイル形式（`tests.py`）は使用しない
- 機能別にテストファイルを分割して保守性を向上させる

### ディレクトリ構造
```
apps/
└── [app_name]/
    ├── tests/
    │   ├── __init__.py
    │   ├── test_models.py      # モデルのテスト
    │   ├── test_views.py       # ビューのテスト
    │   ├── test_forms.py       # フォームのテスト
    │   ├── test_utils.py       # ユーティリティのテスト
    │   └── test_[feature].py   # 機能別テスト
    ├── models.py
    ├── views.py
    └── forms.py
```

### ファイル命名規則
- テストファイル名は`test_`で始める
- テスト対象の機能やモジュール名を含める
- 例：`test_staff_form.py`、`test_client_views.py`、`test_contract_models.py`

### テストクラス命名規則
- テストクラス名は`Test`で終わる
- テスト対象を明確に示す
- 例：`StaffFormTest`、`ClientViewTest`、`ContractModelTest`

### テストメソッド命名規則
- テストメソッド名は`test_`で始める
- テスト内容を説明的に記述
- 日本語のdocstringでテスト内容を説明
- 例：
  ```python
  def test_staff_create_with_valid_data(self):
      """有効なデータでスタッフ作成が成功することをテスト"""
      pass
  ```

## 既存アプリのテスト構成例

### ✅ 良い例（推奨）
```
apps/staff/tests/
├── __init__.py
├── test_models.py
├── test_views.py
├── test_forms.py
├── test_staff_form.py
├── test_staff_qualification.py
├── test_staff_skill.py
├── test_staff_sorting.py
└── test_regist_form_filter.py
```

### ❌ 悪い例（非推奨）
```
apps/api/
└── tests.py  # 単一ファイル形式は使用しない
```

## テスト実行コマンド

### アプリ全体のテスト実行
```bash
python manage.py test apps.staff.tests
```

### 特定のテストファイル実行
```bash
python manage.py test apps.staff.tests.test_staff_form
```

### 特定のテストクラス実行
```bash
python manage.py test apps.staff.tests.test_staff_form.StaffFormTest
```

### 特定のテストメソッド実行
```bash
python manage.py test apps.staff.tests.test_staff_form.StaffFormTest.test_valid_data
```

## テストデータの管理

### フィクスチャファイル
- `_sample_data/`ディレクトリにJSONフィクスチャを配置
- テストで使用するサンプルデータを統一管理

### テストデータベース
- テスト実行時は自動的にテスト用データベースが作成される
- テスト終了後は自動的に削除される

## カバレッジ目標

### 最低限のテストカバレッジ
- **モデル**: 全てのカスタムメソッドとバリデーション
- **フォーム**: 全てのバリデーションルール
- **ビュー**: 主要なCRUD操作
- **ユーティリティ**: 全ての公開メソッド

### テスト種別
1. **単体テスト**: 個別の機能をテスト
2. **統合テスト**: 複数のコンポーネント間の連携をテスト
3. **機能テスト**: ユーザーの操作フローをテスト
