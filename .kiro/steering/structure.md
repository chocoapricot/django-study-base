# プロジェクト構造

## ルートディレクトリレイアウト
```
django-study-base/
├── apps/                    # Djangoアプリケーション（モジュラーコンポーネント）
├── config/                  # プロジェクト設定
├── templates/               # アプリ別に整理されたHTMLテンプレート
├── statics/                 # 静的アセット（CSS、JS、フォント）
├── _sample_data/           # データインポート/エクスポート用JSONフィクスチャ
├── venv/                   # Python仮想環境
├── manage.py               # Django管理スクリプト
└── db.sqlite3             # SQLiteデータベースファイル
```

## アプリディレクトリ構造
各アプリは以下の標準ファイルでDjango規約に従います：
- `models.py`: データベースモデル
- `views.py`: ビューロジック
- `urls.py`: URLルーティング
- `forms.py`: フォーム定義
- `admin.py`: Django管理画面設定
- `apps.py`: アプリ設定
- `migrations/`: データベースマイグレーションファイル

### アプリケーションモジュール
- **`apps/system/`**: コアシステム機能
  - `dropdowns/`: ドロップダウン/選択オプション管理
  - `useradmin/`: カスタムユーザー管理と認証
  - `menu/`: ナビゲーションメニューシステム
  - `parameters/`: システム設定パラメータ
- **`apps/staff/`**: 従業員管理
- **`apps/client/`**: 顧客関係管理
- **`apps/api/`**: REST APIエンドポイント
- **`apps/common/`**: 共有ユーティリティと共通機能
- **`apps/home/`**: ホームページとランディングページ
- **`apps/csstest/`**: CSSテストと開発

## 設定構造
```
config/
├── settings/
│   ├── settings.py         # メイン設定
│   ├── develop.py          # 開発環境固有設定
│   └── product.py          # 本番環境固有設定
├── urls.py                 # ルートURL設定
├── wsgi.py                 # WSGIアプリケーション
└── asgi.py                 # ASGIアプリケーション
```

## テンプレート構成
テンプレートはアプリケーション別に整理され、共通テンプレートはcommonに配置：
```
templates/
├── common/                 # 共有テンプレート
├── registration/           # 認証テンプレート
├── home/                   # ホームページテンプレート
├── staff/                  # スタッフ管理テンプレート
├── client/                 # クライアント管理テンプレート
└── useradmin/             # ユーザー管理テンプレート
```

## 静的アセット
```
statics/
├── css/                    # スタイルシート
├── js/                     # JavaScriptファイル
└── fonts/                  # フォントファイル
```

## 命名規則
- **アプリ**: 小文字、説明的な名前（例：`staff`、`client`）
- **モデル**: パスカルケース（例：`CustomUser`）
- **URL**: 小文字でハイフン区切り（例：`/staff/contact-list/`）
- **テンプレート**: 小文字でアンダースコア区切り（例：`staff_list.html`）
- **静的ファイル**: タイプ別にそれぞれのサブディレクトリで整理

## インポートパターン
- アプリ内では相対インポートを使用：`from .models import MyModel`
- アプリ間参照では絶対インポートを使用：`from apps.common.utils import helper_function`
- システムアプリの参照：`apps.system.useradmin.models.CustomUser`