# Renderへのデプロイ設定

RenderでDjangoアプリを公開するために必要な設定を行いました。

## 実施した変更

1.  **`requirements.txt` の更新**
    *   `dj-database-url`: `DATABASE_URL` 環境変数をDjangoのデータベース設定に変換するために使用。
    *   `psycopg2-binary`: PostgreSQLに接続するためのライブラリ。
2.  **`config/settings/product.py` の修正**
    *   環境変数から `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` を読み込むように設定。
    *   `WhiteNoise` ミドルウェアを追加し、静的ファイルを配信できるように設定。
    *   Renderの PostgreSQL デーベースに接続するための設定を追加。
    *   HTTPSリダイレクトやクッキーのセキュア設定を追加。
3.  **`build.sh` の作成**
    *   Renderのビルド時に実行されるスクリプトです。依存関係のインストール、静的ファイルの収集、マイグレーションを行います。

## Renderダッシュボードでの設定項目

デプロイ時にRenderのダッシュボードで以下の項目を設定してください。

### 1. Web Service の設定
*   **Runtime**: `Python`
*   **Build Command**: `./build.sh`
*   **Start Command**: `gunicorn config.wsgi:application`

### 2. 環境変数 (Environment Variables)
*   **`DJANGO_SETTINGS_MODULE`**: `config.settings.product` (重要)
*   **`SECRET_KEY`**: ランダムな長い文字列
*   **`DEBUG`**: `False`
*   **`ALLOWED_HOSTS`**: `your-app-name.onrender.com`
*   **`DATABASE_URL`**: PostgreSQLデータベースを作成すると自動的に提供されます
*   **`PYTHON_VERSION`**: `3.12.x` (利用しているバージョンに合わせて)

## 補足
*   `build.sh` に実行権限が必要な場合があります（Gitにコミットする前に `chmod +x build.sh` を実行するか、Render側で対応）。
