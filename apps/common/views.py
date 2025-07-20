
from django.shortcuts import render
from .models import AppLog
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
@permission_required('is_superuser', raise_exception=True)
def applog_list(request):
    query = request.GET.get('q', '')
    log_list = AppLog.objects.all().order_by('-timestamp')
    if query:
        log_list = log_list.filter(
            Q(user__username__icontains=query) |
            Q(action__icontains=query) |
            Q(model_name__icontains=query) |
            Q(object_id__icontains=query) |
            Q(object_repr__icontains=query)
        )
    paginator = Paginator(log_list, 20)  # 1ページ20件
    page = request.GET.get('page')
    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)
    return render(request, 'common/applog_list.html', {'logs': logs, 'query': query})
