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

echo 会社データをインポート中...
python manage.py loaddata _sample_data/company.json
if errorlevel 1 goto error

echo 部署データをインポート中...
python manage.py loaddata _sample_data/company_department.json
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

echo クライアント組織データをインポート中...
python manage.py loaddata _sample_data/client_department.json
if errorlevel 1 goto error

echo クライアント担当者データをインポート中...
python manage.py loaddata _sample_data/client_user.json
if errorlevel 1 goto error

echo クライアント連絡履歴データをインポート中...
python manage.py loaddata _sample_data/client_contacted.json
if errorlevel 1 goto error

echo クライアント契約データをインポート中...
python manage.py loaddata _sample_data/contract_client.json
if errorlevel 1 goto error

echo スタッフ契約データをインポート中...
python manage.py loaddata _sample_data/contract_staff.json
if errorlevel 1 goto error

echo.
echo 🎉 サンプルデータのインポートが完了しました！
echo.
echo 📈 インポートされたデータ:
echo - ドロップダウン選択肢
echo - システムパラメータ
echo - メニュー設定
echo - 会社データ
echo - 部署データ
echo - スタッフデータ
echo - スタッフ連絡履歴
echo - クライアントデータ
echo - クライアント組織データ
echo - クライアント担当者データ
echo - クライアント連絡履歴
echo - クライアント契約データ
echo - スタッフ契約データ
goto end

:error
echo ❌ エラーが発生しました
pause
exit /b 1

:end
pause