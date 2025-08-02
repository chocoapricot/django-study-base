# デプロイメントガイド

## Django 5.2.4アップデート後のデプロイ手順

### 1. 依存関係の更新

```bash
# 仮想環境をアクティベート
.\venv\Scripts\Activate

# 依存関係を最新に更新
pip install --upgrade -r requirements.txt

# 更新されたパッケージの確認
pip list --outdated
```

### 2. データベースマイグレーション

```bash
# マイグレーションの確認
python manage.py showmigrations

# マイグレーションの適用
python manage.py migrate

# 必要に応じて特定のアプリのマイグレーション
python manage.py migrate common
python manage.py migrate logs
```

### 3. 静的ファイルの収集（本番環境）

```bash
# 静的ファイルの収集
python manage.py collectstatic --noinput
```

### 4. テストの実行

```bash
# 全テストの実行
python manage.py test

# 特定のアプリのテスト
python manage.py test apps.staff
python manage.py test apps.client
python manage.py test apps.api
```

### 5. 開発サーバーの起動確認

```bash
# 開発サーバー起動
python manage.py runserver

# ブラウザでアクセス確認
# http://127.0.0.1:8000/
```

## トラブルシューティング

### common_applogエラーが発生した場合

```bash
# マイグレーションの状況確認
python manage.py showmigrations common

# 必要に応じて偽装適用
python manage.py migrate common 0005_delete_applog --fake
```

### データベースの整合性確認

```bash
# データベースシェルでテーブル確認
python manage.py dbshell
# または
python -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\";'); print(cursor.fetchall()); conn.close()"
```

## 本番環境での注意事項

1. **設定ファイル**: `config.settings.product`を使用
2. **データベース**: SQLiteから本番用データベース（MySQL等）への移行を検討
3. **静的ファイル**: Webサーバー（Nginx等）での配信設定
4. **セキュリティ**: `DEBUG = False`、`ALLOWED_HOSTS`の適切な設定

## ロールバック手順

万が一問題が発生した場合：

```bash
# 特定のマイグレーションに戻す
python manage.py migrate <app_name> <migration_number>

# 依存関係を前のバージョンに戻す
pip install Django==5.2.1
```