
from django.shortcuts import render
from .models import AppLog
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime

@login_required
@permission_required('is_superuser', raise_exception=True)
def applog_list(request):
    query = request.GET.get('q', '')
    date_filter_raw = request.GET.get('date_filter', '')
    
    log_list = AppLog.objects.all().order_by('-timestamp')
    
    # テキスト検索
    if query:
        log_list = log_list.filter(
            Q(user__username__icontains=query) |
            Q(action__icontains=query) |
            Q(model_name__icontains=query) |
            Q(object_id__icontains=query) |
            Q(object_repr__icontains=query)
        )
    
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
                    date_obj = datetime(int(year), int(month), int(day))
                    log_list = log_list.filter(timestamp__date=date_obj.date())
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
                        log_list = log_list.filter(
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
    
    paginator = Paginator(log_list, 20)  # 1ページ20件
    page = request.GET.get('page')
    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)
    
    context = {
        'logs': logs,
        'query': query,
        'date_filter': date_filter_for_display,  # 表示用（スラッシュ区切り）
        'date_filter_url': date_filter_for_url,  # URLパラメータ用（ハイフン区切り）
    }
    return render(request, 'common/applog_list.html', context)
