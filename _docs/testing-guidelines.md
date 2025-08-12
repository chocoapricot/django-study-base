# テストガイドライン

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

## 継続的インテグレーション

### テスト実行の自動化
- コミット前に関連テストを実行
- プルリクエスト時に全テストを実行
- デプロイ前に全テストが成功することを確認

## 移行ガイド

### 既存の`tests.py`から`tests/`ディレクトリへの移行手順

1. **ディレクトリ作成**
   ```bash
   mkdir apps/[app_name]/tests
   touch apps/[app_name]/tests/__init__.py
   ```

2. **テストファイル分割**
   - 機能別にテストクラスを分割
   - 適切なファイル名で保存

3. **インポート修正**
   - 必要に応じてインポートパスを調整

4. **テスト実行確認**
   - 移行後にテストが正常に実行されることを確認

5. **旧ファイル削除**
   - 移行完了後に`tests.py`を削除

## 注意事項

- テストファイルには必ず`__init__.py`を配置する
- テストクラスは`TestCase`を継承する
- テストメソッドは独立して実行可能にする
- テストデータは各テストで適切にクリーンアップする
- 外部依存（API呼び出しなど）はモックを使用する

## 参考資料

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)