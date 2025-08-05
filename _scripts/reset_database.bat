@echo off
echo データベースリセットを開始します...

REM データベースファイルを削除
if exist db.sqlite3 (
    del db.sqlite3
    echo ✅ db.sqlite3を削除しました
) else (
    echo ℹ️ db.sqlite3は存在しません
)

REM マイグレーションを適用
echo.
echo 📋 マイグレーションを適用中...

echo 設定アプリのマイグレーション作成中...
python manage.py makemigrations settings
if errorlevel 1 goto error

echo ユーザー管理アプリのマイグレーション作成中...
python manage.py makemigrations useradmin
if errorlevel 1 goto error

echo スタッフアプリのマイグレーション作成中...
python manage.py makemigrations staff
if errorlevel 1 goto error

echo クライアントアプリのマイグレーション作成中...
python manage.py makemigrations client
if errorlevel 1 goto error

echo 会社アプリのマイグレーション作成中...
python manage.py makemigrations company
if errorlevel 1 goto error

echo 共通アプリのマイグレーション作成中...
python manage.py makemigrations common
if errorlevel 1 goto error

echo 全体のマイグレーション作成中...
python manage.py makemigrations
if errorlevel 1 goto error

echo データベースマイグレーション適用中...
python manage.py migrate
if errorlevel 1 goto error

echo.
echo.
echo 🎉 データベースマイグレーションが完了しました！
echo.
echo 次のステップ:
echo 1. スーパーユーザーを作成: python manage.py createsuperuser
echo    ※サンプルデータが参照するため、ID=1のユーザーを作成してください
echo 2. サンプルデータをインポート: python _scripts/load_sample_data.py
echo 3. 開発サーバーを起動: python manage.py runserver
goto end

:error
echo ❌ エラーが発生しました
pause
exit /b 1

:end
pause