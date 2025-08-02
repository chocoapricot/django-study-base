@echo off
echo 📊 サンプルデータのインポートを開始します...

REM ファイルの存在確認
if not exist "_sample_data\dropdowns.json" (
    echo ❌ dropdowns.jsonが見つかりません
    goto error
)

echo.
echo 📋 サンプルデータをインポート中...

echo ドロップダウンデータをインポート中...
python manage.py loaddata _sample_data/dropdowns.json
if errorlevel 1 goto error

echo パラメータデータをインポート中...
python manage.py loaddata _sample_data/parameters.json
if errorlevel 1 goto error

echo メニューデータをインポート中...
python manage.py loaddata _sample_data/menus.json
if errorlevel 1 goto error

echo スタッフデータをインポート中...
python manage.py loaddata _sample_data/staff.json
if errorlevel 1 goto error

echo スタッフ連絡履歴データをインポート中...
python manage.py loaddata _sample_data/staff_contacted.json
if errorlevel 1 goto error

echo クライアントデータをインポート中...
python manage.py loaddata _sample_data/client.json
if errorlevel 1 goto error

echo クライアント連絡履歴データをインポート中...
python manage.py loaddata _sample_data/client_contacted.json
if errorlevel 1 goto error

echo.
echo 🎉 サンプルデータのインポートが完了しました！
echo.
echo 📈 インポートされたデータ:
echo - ドロップダウン選択肢
echo - システムパラメータ
echo - メニュー設定
echo - スタッフデータ
echo - スタッフ連絡履歴
echo - クライアントデータ
echo - クライアント連絡履歴
goto end

:error
echo ❌ エラーが発生しました
pause
exit /b 1

:end
pause