import logging
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from .models import Client
from .forms import ClientForm
# from apps.api.helpers import fetch_company_info  # API呼び出し関数をインポート

# ロガーの作成
logger = logging.getLogger('client')

def client_list(request):
    sort = request.GET.get('sort', 'corporate_number')
    query = request.GET.get('q', '').strip()
    clients = Client.objects.all()
    if query:
        clients = clients.filter(
            Q(name__icontains=query)
            | Q(name_furigana__icontains=query)
            | Q(address__icontains=query)
            | Q(memo__icontains=query)
        )
    # ソート可能なフィールドを追加
    sortable_fields = [
        'corporate_number', '-corporate_number',
        'name', '-name',
        'address', '-address',
    ]
    if sort in sortable_fields:
        clients = clients.order_by(sort)
    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page')
    clients_pages = paginator.get_page(page_number)
    return render(request, 'client/client_list.html', {'clients': clients_pages, 'query': query})

def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('client_list')
    else:
        form = ClientForm()
    return render(request, 'client/client_form.html', {'form': form})

def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    # if request.method == 'POST':
    #     form = ClientForm(request.POST, instance=client)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('client_list')
    # else:
    form = ClientForm(instance=client)
    return render(request, 'client/client_detail.html', {'client': client})

def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)
    return render(request, 'client/client_form.html', {'form': form})

def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        return redirect('client_list')
    return render(request, 'client/client_confirm_delete.html', {'client': client})
# views.py



# def get_company_info(request):
#     corporate_number = request.GET.get("corporate_number")
#     if corporate_number:
#         company_info = fetch_company_info(corporate_number)
#         if company_info:
#             return JsonResponse({"success": True, "data": company_info})
#     return JsonResponse({"success": False, "error": "企業情報の取得に失敗しました。"})
