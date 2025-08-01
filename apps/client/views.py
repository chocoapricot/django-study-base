# 連絡履歴 詳細
from django.contrib.auth.decorators import permission_required

@permission_required('client.view_clientcontacted', raise_exception=True)
def client_contacted_detail(request, pk):
    from .models import ClientContacted
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    return render(request, 'client/client_contacted_detail.html', {'contacted': contacted, 'client': client})
from django.contrib.auth.decorators import login_required, permission_required
def client_contacted_detail(request, pk):
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    return render(request, 'client/client_contacted_detail.html', {'contacted': contacted, 'client': client})
import logging
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
# クライアント連絡履歴用インポート
from .models import Client, ClientContacted
from .forms import ClientForm, ClientContactedForm
# from apps.api.helpers import fetch_company_info  # API呼び出し関数をインポート

# ロガーの作成
logger = logging.getLogger('client')

@login_required
@permission_required('client.view_client', raise_exception=True)
def client_list(request):
    sort = request.GET.get('sort', 'corporate_number')
    query = request.GET.get('q', '').strip()
    regist_form_client = request.GET.get('regist_form_client', '').strip()
    
    clients = Client.objects.all()
    
    # キーワード検索
    if query:
        clients = clients.filter(
            Q(name__icontains=query)
            | Q(name_furigana__icontains=query)
            | Q(address__icontains=query)
            | Q(memo__icontains=query)
        )
    
    # 登録区分での絞り込み
    if regist_form_client:
        clients = clients.filter(regist_form_client=regist_form_client)
    
    # ソート可能なフィールドを追加
    sortable_fields = [
        'corporate_number', '-corporate_number',
        'name', '-name',
        'address', '-address',
    ]
    if sort in sortable_fields:
        clients = clients.order_by(sort)
    
    # 登録区分のドロップダウンデータを取得
    from apps.system.dropdowns.models import Dropdowns
    regist_form_options = Dropdowns.objects.filter(
        category='regist_form_client', 
        active=True
    ).order_by('disp_seq')
    
    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page')
    clients_pages = paginator.get_page(page_number)
    
    return render(request, 'client/client_list.html', {
        'clients': clients_pages, 
        'query': query,
        'regist_form_client': regist_form_client,
        'regist_form_options': regist_form_options
    })

@login_required
@permission_required('client.add_client', raise_exception=True)
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('client:client_list')
    else:
        form = ClientForm()
    return render(request, 'client/client_form.html', {'form': form})

@login_required
@permission_required('client.view_client', raise_exception=True)
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(instance=client)
    # 連絡履歴（最新5件）
    contacted_list = client.contacted_histories.all()[:5]
    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    from apps.system.logs.models import AppLog
    log_view_detail(request.user, client)
    # 変更履歴（AppLogから取得、最新5件）
    change_logs = AppLog.objects.filter(model_name='Client', object_id=str(client.pk), action__in=['create', 'update']).order_by('-timestamp')[:5]
    change_logs_count = AppLog.objects.filter(model_name='Client', object_id=str(client.pk), action__in=['create', 'update']).count()
    return render(request, 'client/client_detail.html', {
        'client': client,
        'form': form,
        'contacted_list': contacted_list,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    })

# クライアント変更履歴一覧
@login_required
@permission_required('client.view_client', raise_exception=True)
def client_change_history_list(request, pk):
    client = get_object_or_404(Client, pk=pk)
    from apps.system.logs.models import AppLog
    logs = AppLog.objects.filter(model_name='Client', object_id=str(client.pk), action__in=['create', 'update']).order_by('-timestamp')
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    return render(request, 'client/client_change_history_list.html', {'client': client, 'logs': logs_page})

# クライアント連絡履歴 登録
@login_required
@permission_required('client.add_clientcontacted', raise_exception=True)
def client_contacted_create(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    if request.method == 'POST':
        form = ClientContactedForm(request.POST)
        if form.is_valid():
            contacted = form.save(commit=False)
            contacted.client = client
            contacted.save()
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientContactedForm()
    return render(request, 'client/client_contacted_form.html', {'form': form, 'client': client})

# クライアント連絡履歴 一覧
@login_required
@permission_required('client.view_clientcontacted', raise_exception=True)
def client_contacted_list(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    contacted_qs = client.contacted_histories.all().order_by('-contacted_at')
    paginator = Paginator(contacted_qs, 20)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    return render(request, 'client/client_contacted_list.html', {'client': client, 'logs': logs})

# クライアント連絡履歴 編集
@login_required
@permission_required('client.change_clientcontacted', raise_exception=True)
def client_contacted_update(request, pk):
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    if request.method == 'POST':
        form = ClientContactedForm(request.POST, instance=contacted)
        if form.is_valid():
            form.save()
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientContactedForm(instance=contacted)
    return render(request, 'client/client_contacted_form.html', {'form': form, 'client': client, 'contacted': contacted})

@login_required
@permission_required('client.delete_clientcontacted', raise_exception=True)
def client_contacted_delete(request, pk):
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    if request.method == 'POST':
        contacted.delete()
        return redirect('client:client_detail', pk=client.pk)
    return render(request, 'client/client_contacted_confirm_delete.html', {'contacted': contacted, 'client': client})

@login_required
@permission_required('client.change_client', raise_exception=True)
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    return render(request, 'client/client_form.html', {'form': form})

@login_required
@permission_required('client.delete_client', raise_exception=True)
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        return redirect('client:client_list')
    return render(request, 'client/client_confirm_delete.html', {'client': client})
# views.py



# def get_company_info(request):
#     corporate_number = request.GET.get("corporate_number")
#     if corporate_number:
#         company_info = fetch_company_info(corporate_number)
#         if company_info:
#             return JsonResponse({"success": True, "data": company_info})
#     return JsonResponse({"success": False, "error": "企業情報の取得に失敗しました。"})
