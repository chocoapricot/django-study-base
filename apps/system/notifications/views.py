from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Notification


@login_required
def notification_list(request):
    """
    通知一覧ビュー
    ログインユーザーの通知を表示する
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # ページネーション
    paginator = Paginator(notifications, 20)  # 1ページに20件
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 未読件数
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'page_obj': page_obj,
        'unread_count': unread_count,
    }
    
    return render(request, 'system/notifications/notification_list.html', context)


@login_required
def notification_detail(request, pk):
    """
    通知詳細ビュー
    通知を表示し、自動的に既読にする
    """
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    
    # 未読の場合は既読にする
    if not notification.is_read:
        notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    
    return render(request, 'system/notifications/notification_detail.html', context)


@login_required
def notification_count(request):
    """
    未読通知数を返すAPI
    ヘッダーアイコンのバッジ表示用
    """
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return JsonResponse({
        'unread_count': unread_count
    })


@login_required
def mark_all_as_read(request):
    """
    すべての通知を既読にする
    """
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect('system_notifications:notification_list')
    
    return redirect('system_notifications:notification_list')
