# Renderへのデプロイ設定

RenderでDjangoアプリを公開するために必要な設定を行いました。

## 実施した変更

1.  **`requirements.txt` の更新**
    *   `gunicorn`: WSGIサーバ。
    *   `whitenoise`: 静的ファイル配信ライブラリ。
    *   (PostgreSQL関連の `dj-database-url` や `psycopg2-binary` はSQLite運用の目的で削除済み)
2.  **`config/settings/product.py` の修正**
    *   環境変数から `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` を読み込むように設定。
    *   `WhiteNoise` ミドルウェアを追加し、静的ファイルを配信できるように設定。
    *   Renderの Disk 機能を使用して SQLite データベース (`/data/db.sqlite3`) を永続化する設定に限定。
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
*   **`PYTHON_VERSION`**: `3.12.x` (利用しているバージョンに合わせて)

## 永続化について (SQLite)
Renderの無料プランのWeb Serviceは再起動時にファイルが消えてしまいますが、`render.yaml` で `disk` を設定しているため、`/data/db.sqlite3` に保存されるデータは永続化されます。

## 補足
*   `build.sh` に実行権限が必要な場合があります（Gitにコミットする前に `chmod +x build.sh` を実行するか、Render側で対応）。
