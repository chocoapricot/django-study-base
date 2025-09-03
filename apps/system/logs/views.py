from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import MailLog, AppLog, AccessLog
from django.http import HttpResponse
from .resources import AppLogResource, MailLogResource
import datetime
from django.db.models import Count
from django.urls import get_resolver, URLPattern, URLResolver
from datetime import timedelta

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
                    date_obj = datetime.datetime(int(year), int(month), int(day))
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


@login_required
@permission_required('logs.view_applog', raise_exception=True)
def app_log_export(request):
    """アプリケーション操作ログのエクスポート"""
    query = request.GET.get('q', '')
    date_filter_raw = request.GET.get('date_filter', '')
    format_type = request.GET.get('format', 'csv')

    app_logs = AppLog.objects.select_related('user').order_by('-timestamp')

    if query:
        keywords = [keyword.strip() for keyword in query.split() if keyword.strip()]
        for keyword in keywords:
            keyword_filter = (
                Q(user__username__icontains=keyword) |
                Q(action__icontains=keyword) |
                Q(model_name__icontains=keyword) |
                Q(object_id__icontains=keyword) |
                Q(object_repr__icontains=keyword)
            )
            app_logs = app_logs.filter(keyword_filter)

    if date_filter_raw:
        try:
            date_filter_cleaned = date_filter_raw.strip()
            date_filter_normalized = date_filter_cleaned.replace('/', '-')
            parts = date_filter_normalized.split('-')
            if len(parts) == 3:
                year, month, day = parts
                try:
                    date_obj = datetime.datetime(int(year), int(month), int(day))
                    app_logs = app_logs.filter(timestamp__date=date_obj.date())
                except ValueError:
                    pass
            elif len(parts) == 2:
                year, month = parts
                if 1 <= int(month) <= 12:
                    app_logs = app_logs.filter(timestamp__year=int(year), timestamp__month=int(month))
        except (ValueError, IndexError):
            pass

    resource = AppLogResource()
    dataset = resource.export(app_logs)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format_type == 'excel':
        response = HttpResponse(dataset.xlsx, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="app_logs_{timestamp}.xlsx"'
    else:
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="app_logs_{timestamp}.csv"'
        
    return response


@login_required
@permission_required('logs.view_maillog', raise_exception=True)
def mail_log_export(request):
    """メール送信ログのエクスポート"""
    query = request.GET.get('q', '').strip()
    mail_type = request.GET.get('mail_type', '').strip()
    status = request.GET.get('status', '').strip()
    format_type = request.GET.get('format', 'csv')

    mail_logs = MailLog.objects.all().order_by('-created_at')

    if query:
        mail_logs = mail_logs.filter(
            Q(to_email__icontains=query) |
            Q(subject__icontains=query) |
            Q(from_email__icontains=query)
        )
    if mail_type:
        mail_logs = mail_logs.filter(mail_type=mail_type)
    if status:
        mail_logs = mail_logs.filter(status=status)

    resource = MailLogResource()
    dataset = resource.export(mail_logs)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    if format_type == 'excel':
        response = HttpResponse(dataset.xlsx, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="mail_logs_{timestamp}.xlsx"'
    else:
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="mail_logs_{timestamp}.csv"'
        
    return response


def get_all_urls(url_patterns, parent_pattern=''):
    """
    プロジェクト内のすべてのURLを再帰的にリストアップする
    """
    urls = []
    for pattern in url_patterns:
        if isinstance(pattern, URLResolver):
            # include()されたURLConfの場合、再帰的に探索
            urls.extend(get_all_urls(pattern.url_patterns, parent_pattern + pattern.pattern.regex.pattern))
        elif isinstance(pattern, URLPattern):
            # 通常のURLパターンの場合
            # パターンから正規表現の特殊文字を除去し、整形
            url_path = parent_pattern + pattern.pattern.regex.pattern
            # ^ と $ を削除
            url_path = url_path.strip('^$')
            # URLパラメータ部分（例: <int:pk>）を無視
            import re
            url_path = re.sub(r'<[^>]+>', '', url_path)
            # URLの先頭にスラッシュを追加
            if not url_path.startswith('/'):
                url_path = '/' + url_path
            urls.append(url_path)
    return urls


@login_required
@permission_required('logs.view_accesslog', raise_exception=True)
def access_log_list(request):
    """アクセスログ一覧"""
    # 日付範囲フィルタ
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    access_logs = AccessLog.objects.all()

    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            access_logs = access_logs.filter(timestamp__gte=start_date)
        except ValueError:
            start_date_str = None
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
            access_logs = access_logs.filter(timestamp__lt=end_date + timedelta(days=1))
        except ValueError:
            end_date_str = None

    # URLごとのアクセス数を集計
    access_counts = access_logs.values('url').annotate(count=Count('id')).order_by('url')
    access_counts_dict = {item['url']: item['count'] for item in access_counts}

    # プロジェクトの全URLリストを取得
    resolver = get_resolver()
    all_urls = sorted(list(set(get_all_urls(resolver.url_patterns))))

    # 全URLとアクセス数を結合
    url_data = []
    for url in all_urls:
        # adminとaccountsは除外
        if not url.startswith('/admin') and not url.startswith('/accounts'):
            url_data.append({
                'url': url,
                'count': access_counts_dict.get(url, 0)
            })

    # ソート
    sort = request.GET.get('sort', 'url')
    reverse = sort.startswith('-')
    sort_key = sort.lstrip('-')

    if sort_key in ['url', 'count']:
        url_data.sort(key=lambda x: x[sort_key], reverse=reverse)

    context = {
        'url_data': url_data,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'sort': sort,
    }

    return render(request, 'logs/access_log_list.html', context)
