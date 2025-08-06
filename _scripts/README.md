# スクリプト集

このディレクトリには、プロジェクトの管理・運用に使用するスクリプトが含まれています。

## データベース管理

### reset_database.py / reset_database.bat
データベースを削除して、正しい順序でマイグレーションを適用します。

**使用方法:**
```bash
# Pythonスクリプト版
python _scripts/reset_database.py

# Windowsバッチファイル版
_scripts/reset_database.bat
```

**機能:**
- db.sqlite3ファイルの削除
- データベースマイグレーションの適用
- エラーハンドリングと詳細なログ出力
- 次のステップの案内（スーパーユーザー作成、サンプルデータインポート）

## サンプルデータ管理

### load_sample_data.py / load_sample_data.bat
サンプルデータを正しい順序でインポートします。

**使用方法:**
```bash
# Pythonスクリプト版
python _scripts/load_sample_data.py

# Windowsバッチファイル版
_scripts/load_sample_data.bat
```

**機能:**
- 依存関係を考慮したサンプルデータのインポート
- ファイル存在確認
- エラーハンドリング

**前提条件:**
- スーパーユーザー（ID=1）が作成済みであること

**インポート順序:**
1. dropdowns.json - ドロップダウン選択肢
2. parameters.json - システムパラメータ
3. menus.json - メニュー設定
4. company.json - 会社データ
5. company_department.json - 部署データ
6. staff.json - スタッフデータ
7. staff_contacted.json - スタッフ連絡履歴
8. client.json - クライアントデータ
9. client_department.json - クライアント組織データ
10. client_user.json - クライアント担当者データ
11. client_contacted.json - クライアント連絡履歴

## 注意事項

- スクリプトはプロジェクトルートディレクトリから実行してください
- 仮想環境がアクティベートされていることを確認してください
- データベースリセット前には重要なデータのバックアップを取ってください