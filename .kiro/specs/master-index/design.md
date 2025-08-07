# マスタ一覧画面 設計書

## 概要

システムで管理する各種マスタデータへの統一的なアクセスポイントとして、マスタ一覧画面を設計する。テーブル形式でマスタ情報を表示し、各マスタのカテゴリ数、データ数、総件数を表示する拡張可能な設計とする。

## アーキテクチャ

### MVC構成
- **Model**: 既存のQualification、Skillモデルを活用
- **View**: master_index_list.htmlテンプレート
- **Controller**: apps.master.views.master_index_list ビュー

### URL構成
```
/master/ - マスタ一覧画面
/master/qualification/ - 資格マスタ一覧（既存）
/master/skill/ - 技能マスタ一覧（既存）
```

## コンポーネントと インターフェース

### 1. マスタ一覧ビュー (master_index_list)

**責任**: マスタ一覧画面の表示とデータ集計

**インターフェース**:
```python
def master_index_list(request):
    """
    マスタ一覧画面を表示
    
    Returns:
        HttpResponse: マスタ一覧画面のHTML
    """
```

**処理フロー**:
1. 利用可能なマスタデータの定義を取得
2. 各マスタのデータ件数を集計
3. テンプレートにデータを渡して表示

### 2. マスタ設定データ構造

**マスタ定義**:
```python
MASTER_CONFIGS = [
    {
        'name': '資格管理',
        'description': '資格・免許・認定等の管理',
        'model': 'master.Qualification',
        'url_name': 'master:qualification_list',
        'icon': 'bi-award',
        'permission': 'master.view_qualification'
    },
    {
        'name': '技能管理', 
        'description': 'スキル・技術・能力等の管理',
        'model': 'master.Skill',
        'url_name': 'master:skill_list',
        'icon': 'bi-tools',
        'permission': 'master.view_skill'
    }
]
```

### 3. データ集計ロジック

**カテゴリ数集計**:
```python
def get_category_count(model_class):
    """レベル1（カテゴリ）のデータ数を取得"""
    return model_class.objects.filter(level=1, is_active=True).count()
```

**データ数集計**:
```python
def get_data_count(model_class):
    """レベル2（データ）のデータ数を取得"""
    return model_class.objects.filter(level=2, is_active=True).count()
```

### 4. テンプレート構造

**master_index_list.html**:
```html
{% extends 'common/_base.html' %}

{% block content %}
<div class="content-box card bg-light mt-2 mb-4">
    <div class="card-header">
        <h5>マスタ管理</h5>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>マスタ名</th>
                        <th>説明</th>
                        <th>カテゴリ数</th>
                        <th>データ数</th>
                        <th>総件数</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for master in masters %}
                    <tr>
                        <td>{{ master.name }}</td>
                        <td>{{ master.description }}</td>
                        <td>{{ master.category_count }}件</td>
                        <td>{{ master.data_count }}件</td>
                        <td>{{ master.total_count }}件</td>
                        <td>
                            <a href="{{ master.url }}" class="btn btn-sm btn-primary">
                                <i class="{{ master.icon }}"></i> 管理
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

## データモデル

### マスタ情報データ構造

```python
class MasterInfo:
    """マスタ情報を格納するデータクラス"""
    def __init__(self, name, description, model_class, url_name, icon, permission):
        self.name = name
        self.description = description
        self.model_class = model_class
        self.url_name = url_name
        self.icon = icon
        self.permission = permission
        self.category_count = 0
        self.data_count = 0
        self.total_count = 0
        self.url = ''
```

### 既存モデルの活用

- **Qualification**: 資格マスタデータ
  - level=1: カテゴリ
  - level=2: 資格データ
  
- **Skill**: 技能マスタデータ
  - level=1: カテゴリ
  - level=2: 技能データ

## エラーハンドリング

### 権限エラー
- 権限のないユーザーがアクセスした場合は403エラー
- メニューでは権限チェックにより非表示

### データ取得エラー
- モデルクラスが存在しない場合のエラーハンドリング
- データベース接続エラーの処理

### URL生成エラー
- 存在しないURL名の場合のフォールバック処理

## テスト戦略

### 単体テスト
1. **ビューテスト**
   - 正常なマスタ一覧表示
   - 権限チェック
   - データ件数の正確性

2. **データ集計テスト**
   - カテゴリ数集計の正確性
   - データ数集計の正確性
   - 総件数計算の正確性

3. **権限テスト**
   - 適切な権限でのアクセス
   - 権限なしでのアクセス拒否

### 統合テスト
1. **画面遷移テスト**
   - メニューからマスタ一覧への遷移
   - マスタ一覧から各マスタ管理画面への遷移

2. **レスポンシブテスト**
   - 各デバイスサイズでの表示確認

## セキュリティ考慮事項

### 認証・認可
- ログイン必須
- 適切な権限チェック（view_qualification, view_skill）

### データ保護
- SQLインジェクション対策（ORMの活用）
- XSS対策（テンプレートエスケープ）

## パフォーマンス考慮事項

### データベースアクセス最適化
- 必要最小限のクエリ実行
- カウント処理の効率化

### キャッシュ戦略
- マスタ件数のキャッシュ（将来的な拡張）

## 拡張性設計

### 新しいマスタの追加
1. MASTER_CONFIGSに新しいマスタ定義を追加
2. 対応するモデル、ビュー、URLを実装
3. 権限設定を追加

### 設定の外部化
- 将来的にはデータベースまたは設定ファイルでマスタ定義を管理
- 動的なマスタ追加・削除機能

### 国際化対応
- マスタ名、説明の多言語対応
- テンプレートの国際化

## UI/UX設計

### レスポンシブデザイン
- Bootstrap 5のテーブルレスポンシブ機能を活用
- モバイルでは横スクロール対応

### アクセシビリティ
- 適切なARIAラベル
- キーボードナビゲーション対応
- スクリーンリーダー対応

### ユーザビリティ
- 直感的なアイコン使用
- 分かりやすいボタンラベル
- ホバー効果による視覚的フィードバック