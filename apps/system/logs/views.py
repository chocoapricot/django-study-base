from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from datetime import datetime
from .models import MailLog, AppLog

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


@login_required
@permission_required('logs.view_applog', raise_exception=True)
def app_log_list(request):
    """アプリケーション操作ログ一覧"""
    query = request.GET.get('q', '')
    date_filter_raw = request.GET.get('date_filter', '')
    
    app_logs = AppLog.objects.select_related('user').order_by('-timestamp')
    
    # テキスト検索（複数キーワードのAND検索対応）
    if query:
        # 半角スペースで分割してキーワードリストを作成
        keywords = [keyword.strip() for keyword in query.split() if keyword.strip()]
        
        # 各キーワードに対してOR条件を作成し、それらをANDで結合
        for keyword in keywords:
            keyword_filter = (
                Q(user__username__icontains=keyword) |
                Q(action__icontains=keyword) |
                Q(model_name__icontains=keyword) |
                Q(object_id__icontains=keyword) |
                Q(object_repr__icontains=keyword)
            )
            app_logs = app_logs.filter(keyword_filter)
    
    # 日付検索（年月日または年月）
    date_filter_for_url = ''  # URLパラメータ用（ハイフン区切り）
    date_filter_for_display = ''  # 表示用（スラッシュ区切り）
    
    if date_filter_raw:
        try:
            date_filter_cleaned = date_filter_raw.strip()  # 前後の空白を除去
            # スラッシュをハイフンに変換（内部処理用）
            date_filter_normalized = date_filter_cleaned.replace('/', '-')
            
            # ハイフンで分割して解析
            parts = date_filter_normalized.split('-')
            
            if len(parts) == 3:
                # 年月日形式（YYYY-M-D または YYYY-MM-DD）
                year, month, day = parts
                try:
                    # 日付オブジェクトを作成して妥当性をチェック
                    from datetime import datetime
                    date_obj = datetime(int(year), int(month), int(day))
                    app_logs = app_logs.filter(timestamp__date=date_obj.date())
                    # 0埋めした形式でURLパラメータを作成
                    date_filter_for_url = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                    # 表示用は入力された形式を保持
                    date_filter_for_display = date_filter_cleaned
                except ValueError:
                    # 無効な日付の場合は無視
                    pass
                    
            elif len(parts) == 2:
                # 年月形式（YYYY-M または YYYY-MM）
                year, month = parts
                try:
                    # 年月の妥当性をチェック
                    if 1 <= int(month) <= 12:
                        app_logs = app_logs.filter(
                            timestamp__year=int(year),
                            timestamp__month=int(month)
                        )
                        # 0埋めした形式でURLパラメータを作成
                        date_filter_for_url = f"{int(year):04d}-{int(month):02d}"
                        # 表示用は入力された形式を保持
                        date_filter_for_display = date_filter_cleaned
                except ValueError:
                    # 無効な年月の場合は無視
                    pass
                    
        except (ValueError, IndexError) as e:
            # 無効な日付形式の場合は無視
            print(f"日付フィルターエラー: {date_filter_raw}, エラー: {e}")  # デバッグ用
            pass
    
    # ページネーション
    paginator = Paginator(app_logs, 20)  # 1ページ20件
    page = request.GET.get('page')
    try:
        app_logs_page = paginator.page(page)
    except PageNotAnInteger:
        app_logs_page = paginator.page(1)
    except EmptyPage:
        app_logs_page = paginator.page(paginator.num_pages)
    
    context = {
        'app_logs': app_logs_page,
        'query': query,
        'date_filter': date_filter_for_display,  # 表示用（スラッシュ区切り）
        'date_filter_url': date_filter_for_url,  # URLパラメータ用（ハイフン区切り）
    }
    
    return render(request, 'logs/app_log_list.html', context)


