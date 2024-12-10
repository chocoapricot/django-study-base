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
    query = request.GET.get('q')  # 検索キーワードを取得
    if query:
        query = query.strip()
        clients = Client.objects.filter(
            Q(name__icontains=query)
            |Q(name_furigana__icontains=query)
            |Q(address__icontains=query)
            |Q(memo__icontains=query)
            )
    else:
        query = ''
        clients = Client.objects.all()  # 検索キーワードがなければ全件取得
    paginator = Paginator(clients, 10)  # 1ページあたり10件表示
    page_number = request.GET.get('page')  # URLからページ番号を取得
    clients_pages = paginator.get_page(page_number)  # ページオブジェクトを取得

    return render(request, 'client/client_list.html', {'clients': clients_pages, 'query': query}) # 検索条件再表示

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
