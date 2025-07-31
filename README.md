# Django Study Base

Django学習用のプロジェクトです。スタッフ管理とクライアント管理機能を持つビジネス管理システムを通じて、Djangoの基本的な機能から応用まで学習することを目的としています。Django 5.2.1をベースに構築され、日本語環境に最適化されています。

> **注意**: このプロジェクトは個人の学習目的で作成されており、実際のビジネス用途での使用は想定していません。

## 🚀 主な機能

### 📊 管理機能
- **スタッフ管理**: 従業員データの管理と追跡
- **クライアント管理**: 顧客関係管理機能
- **連絡履歴管理**: スタッフ・クライアントとの連絡記録

### 🔐 認証・セキュリティ
- **カスタムユーザー認証**: django-allauthベースの認証システム
- **ロールベースアクセス制御**: 権限管理機能
- **パスワードバリデーション**: カスタムパスワード要件

### 🛠️ システム管理
- **ドロップダウン管理**: 選択肢の動的管理
- **パラメータ管理**: システム設定の管理
- **メニュー管理**: ナビゲーション設定

### 📱 UI/UX
- **レスポンシブデザイン**: Bootstrap 5ベース
- **日本語対応**: 完全な日本語ローカライゼーション
- **直感的なインターフェース**: 使いやすいUI設計

## 🛠️ 技術スタック

### フレームワーク & コア
- **Django 5.2.1**: メインWebフレームワーク
- **Python 3.12**: バックエンド言語
- **SQLite**: デフォルトデータベース（MySQL対応可能）

### 主要な依存関係
- `django-allauth==65.10.0`: 認証システム
- `django-import-export==4.3.7`: データインポート/エクスポート
- `django-currentuser==0.9.0`: 現在のユーザー追跡
- `pillow==11.2.1`: 画像処理
- `openpyxl==3.1.5`: Excelファイル処理
- `PyMuPDF==1.25.5`: PDF処理
- `requests==2.32.3`: HTTP通信

### フロントエンド
- **Bootstrap 5**: UIフレームワーク
- **Bootstrap Icons**: アイコンセット
- **レスポンシブデザイン**: モバイル対応

## 📁 プロジェクト構造

```
django-study-base/
├── apps/                    # Djangoアプリケーション
│   ├── system/             # システム管理
│   │   ├── dropdowns/      # ドロップダウン管理
│   │   ├── useradmin/      # ユーザー管理
│   │   ├── menu/           # メニュー管理
│   │   └── parameters/     # パラメータ管理
│   ├── staff/              # スタッフ管理
│   ├── client/             # クライアント管理
│   ├── accounts/           # 認証システム
│   ├── common/             # 共通機能
│   └── api/                # REST API
├── config/                 # プロジェクト設定
├── templates/              # HTMLテンプレート
├── statics/                # 静的ファイル
├── _sample_data/          # サンプルデータ
└── requirements.txt        # 依存関係
```

## 🚀 セットアップ

### 前提条件
- Python 3.12以上
- pip（Python パッケージマネージャー）

### インストール手順

1. **プロジェクトのダウンロード**
```bash
# GitHubからダウンロードまたはクローン
git clone [このリポジトリのURL]
cd django-study-base
```

2. **仮想環境の作成とアクティベート**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **依存関係のインストール**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **データベースのセットアップ**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **スーパーユーザーの作成**
```bash
python manage.py createsuperuser
```

6. **開発サーバーの起動**
```bash
python manage.py runserver
```

7. **ブラウザでアクセス**
```
http://127.0.0.1:8000/
```

## 🧪 テスト

### テストの実行
```bash
# 全テストの実行
python manage.py test

# 特定のアプリのテスト
python manage.py test apps.staff
python manage.py test apps.client

# 詳細出力でのテスト実行
python manage.py test --verbosity=2
```

### テストカバレッジ
- 認証システム: ✅ 完全対応
- スタッフ管理: ✅ CRUD操作テスト
- クライアント管理: ✅ CRUD操作テスト
- API エンドポイント: ✅ 基本テスト

## 📊 データ管理

### データのエクスポート
```bash
python manage.py dumpdata staff --format=json --indent=4 > _sample_data/staff.json
python manage.py dumpdata client --format=json --indent=4 > _sample_data/client.json
```

### データのインポート
```bash
python manage.py loaddata _sample_data/staff.json
python manage.py loaddata _sample_data/client.json
```

## 🔧 設定

### 環境設定
- **開発環境**: `config/settings/settings.py`
- **テスト環境**: `config/settings/test.py`
- **本番環境**: `config/settings/product.py`

### 主要設定項目
```python
# 言語・タイムゾーン
LANGUAGE_CODE = 'ja-JP'
TIME_ZONE = 'Asia/Tokyo'

# 認証設定
AUTH_USER_MODEL = 'useradmin.CustomUser'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'

# メール設定（開発環境）
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## 🌐 API

### REST APIエンドポイント
- `/api/staff/` - スタッフ管理API
- `/api/client/` - クライアント管理API

### 認証
- django-allauthベースの認証
- セッション認証対応

## 🎨 UI/UX

### デザインシステム
- **カラーパレット**: Bootstrap 5準拠
- **タイポグラフィ**: 日本語フォント最適化
- **レスポンシブ**: モバイルファースト設計

### アクセシビリティ
- WCAG 2.1準拠
- キーボードナビゲーション対応
- スクリーンリーダー対応

## 🚀 デプロイ

### 本番環境での設定
1. 環境変数の設定
2. データベースの設定（MySQL推奨）
3. 静的ファイルの収集
4. WSGIサーバーの設定

```bash
# 静的ファイルの収集
python manage.py collectstatic

# 本番用データベースマイグレーション
python manage.py migrate --settings=config.settings.product
```

## 📚 学習内容

このプロジェクトを通じて以下のDjango機能を学習できます：

### 基本機能
- **MVCアーキテクチャ**: Model-View-Template パターン
- **URL設計**: URLconf とルーティング
- **テンプレートシステム**: Django Template Language
- **フォーム処理**: ModelForm とバリデーション

### 応用機能
- **認証システム**: django-allauth を使用したカスタム認証
- **権限管理**: Permission とグループ管理
- **データベース設計**: リレーション設計とマイグレーション
- **テスト**: Unit Test とIntegration Test

### 実践的な機能
- **CRUD操作**: 基本的なデータ操作
- **検索・ソート**: QuerySet の活用
- **ページネーション**: 大量データの表示
- **ファイル処理**: Excel/PDF の生成・処理

## 🎯 学習のポイント

### コーディング規約
- PEP 8準拠のコード記述
- 日本語コメントでの理解促進
- テストコードによる品質確保

## 📝 ライセンス

このプロジェクトは学習目的で作成されており、個人利用に限定されます。

## � 学習記ト録

### 実装済み機能
- ✅ ユーザー認証システム
- ✅ スタッフ管理CRUD
- ✅ クライアント管理CRUD
- ✅ 権限ベースアクセス制御
- ✅ レスポンシブUI（Bootstrap 5）
- ✅ テストコード

### 学習中の課題
- 🔄 API設計とRESTful実装
- 🔄 パフォーマンス最適化
- 🔄 セキュリティ強化

## 🏆 謝辞

このプロジェクトは以下のオープンソースプロジェクトを使用しています：
- [Django](https://djangoproject.com/)
- [Bootstrap](https://getbootstrap.com/)
- [django-allauth](https://django-allauth.readthedocs.io/)

## 📈 今後の学習予定

### 学習したい機能
- [ ] REST API の詳細実装
- [ ] WebSocket を使用したリアルタイム機能
- [ ] キャッシュシステムの導入
- [ ] ログ管理とモニタリング
- [ ] Docker を使用したコンテナ化
- [ ] CI/CD パイプラインの構築

## 🎓 参考資料

- [Django公式ドキュメント](https://docs.djangoproject.com/)
- [django-allauth ドキュメント](https://django-allauth.readthedocs.io/)
- [Bootstrap 5 ドキュメント](https://getbootstrap.com/docs/5.0/)

---

**Django Study Base** - Django学習のための実践プロジェクト 📚