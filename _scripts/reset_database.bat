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