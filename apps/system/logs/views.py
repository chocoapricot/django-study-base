from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import MailLog

@login_required
@permission_required('logs.view_maillog', raise_exception=True)
def mail_log_list(request):
    """メール送信ログ一覧"""
    # 検索とフィルタリング
    query = request.GET.get('q', '').strip()
    mail_type = request.GET.get('mail_type', '').strip()
    status = request.GET.get('status', '').strip()
    
    mail_logs = MailLog.objects.all()
    
    # キーワード検索
    if query:
        mail_logs = mail_logs.filter(
            Q(to_email__icontains=query) |
            Q(subject__icontains=query) |
            Q(from_email__icontains=query)
        )
    
    # メール種別フィルタ
    if mail_type:
        mail_logs = mail_logs.filter(mail_type=mail_type)
    
    # 送信状況フィルタ
    if status:
        mail_logs = mail_logs.filter(status=status)
    
    # ソート
    sort = request.GET.get('sort', '-created_at')
    sortable_fields = [
        'created_at', '-created_at',
        'sent_at', '-sent_at',
        'to_email', '-to_email',
        'mail_type', '-mail_type',
        'status', '-status'
    ]
    
    if sort in sortable_fields:
        mail_logs = mail_logs.order_by(sort)
    else:
        mail_logs = mail_logs.order_by('-created_at')
    
    # ページネーション
    paginator = Paginator(mail_logs, 20)
    page_number = request.GET.get('page')
    mail_logs_page = paginator.get_page(page_number)
    
    # フィルタ選択肢
    mail_type_choices = MailLog.MAIL_TYPE_CHOICES
    status_choices = MailLog.STATUS_CHOICES
    
    context = {
        'mail_logs': mail_logs_page,
        'query': query,
        'mail_type': mail_type,
        'status': status,
        'sort': sort,
        'mail_type_choices': mail_type_choices,
        'status_choices': status_choices,
    }
    
    return render(request, 'logs/mail_log_list.html', context)

@login_required
@permission_required('logs.view_maillog', raise_exception=True)
def mail_log_detail(request, pk):
    """メール送信ログ詳細"""
    mail_log = get_object_or_404(MailLog, pk=pk)
    
    context = {
        'mail_log': mail_log,
    }
    
    return render(request, 'logs/mail_log_detail.html', context)