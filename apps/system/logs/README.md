# システムログアプリ

## 概要
`apps.system.logs`は、システム内の各種ログを管理するアプリケーションです。

## 機能
- **MailLog**: メール送信ログの管理
- **AppLog**: アプリケーション操作ログの管理

## AppLogの使用方法

### 基本的な使用方法

```python
from apps.system.logs.models import AppLog
from apps.system.logs.utils import log_model_action, log_view_detail, log_user_action

# 1. モデル操作のログ記録
user = request.user
instance = MyModel.objects.get(pk=1)
log_model_action(user, 'create', instance)

# 2. 詳細画面アクセスのログ記録
log_view_detail(user, instance)

# 3. ユーザー操作のログ記録
log_user_action(user, 'login', 'ユーザーがログインしました')
```

### ビューでの使用例

```python
from django.shortcuts import render, get_object_or_404
from apps.system.logs.utils import log_view_detail, log_model_action

def my_detail_view(request, pk):
    instance = get_object_or_404(MyModel, pk=pk)
    
    # 詳細画面アクセスをログに記録
    log_view_detail(request.user, instance)
    
    return render(request, 'my_template.html', {'object': instance})

def my_create_view(request):
    if request.method == 'POST':
        form = MyModelForm(request.POST)
        if form.is_valid():
            instance = form.save()
            
            # 作成操作をログに記録
            log_model_action(request.user, 'create', instance)
            
            return redirect('success_url')
    else:
        form = MyModelForm()
    
    return render(request, 'my_form.html', {'form': form})
```

## 移行について

このAppLogモデルは、`apps.common.models.AppLog`からの移行版です。
完全に動作確認が取れた後、元のAppLogを削除する予定です。

### 移行手順
1. 新しいAppLogモデルの動作確認
2. 既存コードの新しいAppLogへの切り替え
3. 元のcommon.AppLogの削除
4. データベースのクリーンアップ

## URL
- アプリケーション操作ログ一覧: `/logs/app/`
- アプリケーション操作ログ詳細: `/logs/app/<id>/`
- メール送信ログ一覧: `/logs/mail/`
- メール送信ログ詳細: `/logs/mail/<id>/`