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
import re

@login_required
@permission_required('logs.view_maillog', raise_exception=True)
def mail_log_list(request):
    """メール送信ログ一覧"""
    query = request.GET.get('q', '').strip()
    mail_type = request.GET.get('mail_type', '').strip()
    status = request.GET.get('status', '').strip()
    
    mail_logs = MailLog.objects.all()
    
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
    
    paginator = Paginator(mail_logs, 20)
    page_number = request.GET.get('page')
    mail_logs_page = paginator.get_page(page_number)
    
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
    
    date_filter_for_url = ''
    date_filter_for_display = ''
    
    if date_filter_raw:
        try:
            date_filter_cleaned = date_filter_raw.strip()
            date_filter_normalized = date_filter_cleaned.replace('/', '-')
            parts = date_filter_normalized.split('-')
            
            if len(parts) == 3:
                year, month, day = parts
                date_obj = datetime.datetime(int(year), int(month), int(day))
                app_logs = app_logs.filter(timestamp__date=date_obj.date())
                date_filter_for_url = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                date_filter_for_display = date_filter_cleaned
            elif len(parts) == 2:
                year, month = parts
                if 1 <= int(month) <= 12:
                    app_logs = app_logs.filter(
                        timestamp__year=int(year),
                        timestamp__month=int(month)
                    )
                    date_filter_for_url = f"{int(year):04d}-{int(month):02d}"
                    date_filter_for_display = date_filter_cleaned
        except (ValueError, IndexError):
            pass
    
    paginator = Paginator(app_logs, 20)
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
        'date_filter': date_filter_for_display,
        'date_filter_url': date_filter_for_url,
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


def get_url_patterns(url_patterns, parent_route=''):
    """
    Recursively collect URL patterns from the project, returning a list of
    tuples: (compiled regex, clean URL string).
    """
    patterns = []
    for p in url_patterns:
        # The string representation of the pattern
        route_str = str(p.pattern)

        if isinstance(p, URLResolver):
            # Recurse for included URLconfs
            patterns.extend(get_url_patterns(p.url_patterns, parent_route + route_str))
        elif isinstance(p, URLPattern):
            full_route = parent_route + route_str

            # Convert Django path converters to regex
            regex_str = re.sub(r'<int:[^>]+>', r'[0-9]+', full_route)
            regex_str = re.sub(r'<str:[^>]+>', r'[^/]+', regex_str)
            regex_str = re.sub(r'<slug:[^>]+>', r'[-a-zA-Z0-9_]+', regex_str)
            regex_str = re.sub(r'<uuid:[^>]+>', r'[0-9a-fA-F-]+', regex_str)
            regex_str = re.sub(r'<path:[^>]+>', r'.+', regex_str)

            # Create the user-friendly "clean" URL
            clean_url = '/' + re.sub(r'<[^>]+>', '#', full_route).replace('//', '/')

            # Compile the final regex. It must match the full path.
            # The path from request.path starts with '/', so the regex should too.
            final_regex = f'^/{regex_str}$'

            try:
                patterns.append((re.compile(final_regex), clean_url))
            except re.error:
                continue
    return patterns

@login_required
@permission_required('logs.view_accesslog', raise_exception=True)
def access_log_list(request):
    """アクセスログ一覧"""
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    logs_qs = AccessLog.objects.all()

    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            logs_qs = logs_qs.filter(timestamp__gte=start_date)
        except ValueError:
            start_date_str = ''
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
            logs_qs = logs_qs.filter(timestamp__lt=end_date + timedelta(days=1))
        except ValueError:
            end_date_str = ''

    access_counts = logs_qs.values('url').annotate(count=Count('id'))

    resolver = get_resolver()
    url_patterns_map = get_url_patterns(resolver.url_patterns)

    pattern_counts = {clean_url: 0 for _, clean_url in url_patterns_map}

    for item in access_counts:
        raw_url = item['url']
        count = item['count']

        for compiled_regex, clean_pattern in url_patterns_map:
            # Match the raw URL from the DB against the compiled regex
            if compiled_regex.fullmatch(raw_url):
                pattern_counts[clean_pattern] += count
                break

    url_data = [{'url': url, 'count': count} for url, count in pattern_counts.items()]

    # Exclude admin URLs from the final list
    url_data = [item for item in url_data if not item['url'].startswith('/admin')]

    sort = request.GET.get('sort', 'url')
    reverse = sort.startswith('-')
    sort_key = sort.lstrip('-')

    if sort_key in ['url', 'count']:
        url_data.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse)

    context = {
        'url_data': url_data,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'sort': sort,
    }

    return render(request, 'logs/access_log_list.html', context)
