from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.urls import reverse
from .models import Company, CompanyDepartment, CompanyUser
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.system.logs.models import AppLog
from apps.system.logs.utils import log_view_detail, log_model_action
from django.db.models import Q
from django.core.paginator import Paginator
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from .forms import CompanyForm, CompanyDepartmentForm, CompanyUserForm, CompanySealUploadForm
from apps.common.middleware import set_current_tenant_id

def get_current_company(request, pk=None, obj=None):
    """
    現在のコンテキストにおける会社オブジェクトを取得するヘルパー関数。
    1. 管理者（スーパーユーザー）の場合：
       - pk または GET.company_id があればそれを優先しセッションを更新。
       - オブジェクト(obj)が渡されていればそのテナントを優先。
       - セッションに保存されているテナントがあればそれを返す。
       - いずれもなければ自身の tenant_id、それもなければ最初の会社。
    2. 一般ユーザーの場合：
       - 自身の tenant_id に固定。なければ 404。
    """
    # 管理者（スーパーユーザー）の場合
    if request.user.is_superuser:
        # 1. パラメータ(pk)やGETパラメータからの指定を優先
        target_id = pk or request.GET.get('company_id')
        if target_id:
            try:
                # Company.pk を取得
                company = Company.objects.get(pk=target_id)
                request.session['current_tenant_id'] = company.tenant_id
                set_current_tenant_id(company.tenant_id)
                return company
            except (Company.DoesNotExist, ValueError):
                pass

        # 2. オブジェクトが渡されている場合はそのテナント
        if obj and hasattr(obj, 'tenant_id'):
            try:
                company = Company.objects.get(tenant_id=obj.tenant_id)
                request.session['current_tenant_id'] = company.tenant_id
                set_current_tenant_id(company.tenant_id)
                return company
            except Company.DoesNotExist:
                pass

        # 3. セッションから取得
        session_tenant_id = request.session.get('current_tenant_id')
        if session_tenant_id:
            try:
                company = Company.objects.get(tenant_id=session_tenant_id)
                set_current_tenant_id(company.tenant_id)
                return company
            except Company.DoesNotExist:
                pass

        # 4. 自身のアカウントに紐づくテナントがあればそれを初期値にする
        if request.user.tenant_id:
            try:
                company = Company.objects.get(tenant_id=request.user.tenant_id)
                request.session['current_tenant_id'] = company.tenant_id
                set_current_tenant_id(company.tenant_id)
                return company
            except Company.DoesNotExist:
                pass

        # 5. それでもなければ最初の会社
        company = Company.objects.first()
        if not company:
            company = Company.objects.create(name="新規会社")
            log_model_action(request.user, 'create', company)
        
        request.session['current_tenant_id'] = company.tenant_id
        set_current_tenant_id(company.tenant_id)
        return company

    # 一般ユーザー（非スーパーユーザー）の場合
    if request.user.tenant_id:
        try:
            company = Company.objects.get(tenant_id=request.user.tenant_id)
            # セッションを同期（他で利用するため）
            request.session['current_tenant_id'] = company.tenant_id
            set_current_tenant_id(company.tenant_id)
            return company
        except Company.DoesNotExist:
            raise Http404("所属する会社情報が見つかりません。")

    # 管理者でなく、tenant_idもない場合はアクセス拒否
    raise Http404("所属する会社が設定されていないため、情報を表示できません。")

def get_company_change_logs(company, limit=None):
    """会社に関連する変更ログを取得するヘルパー関数"""
    company_logs = AppLog.objects.filter(
        model_name='Company',
        object_id=str(company.pk),
        action__in=['create', 'update']
    )

    department_ids = [str(d.pk) for d in CompanyDepartment.objects.filter(tenant_id=company.tenant_id)]
    department_logs = AppLog.objects.filter(
        model_name='CompanyDepartment',
        object_id__in=department_ids,
        action__in=['create', 'update', 'delete']
    )

    company_users = CompanyUser.objects.filter(tenant_id=company.tenant_id)
    company_user_ids = [str(user.pk) for user in company_users]
    company_user_logs = AppLog.objects.filter(
        model_name='CompanyUser',
        object_id__in=company_user_ids,
        action__in=['create', 'update', 'delete']
    )

    all_logs = (company_logs | department_logs | company_user_logs).order_by('-timestamp')
    count = all_logs.count()
    if limit:
        all_logs = all_logs[:limit]
    return all_logs, count

@login_required
@permission_required('company.view_company', raise_exception=True)
def company_detail(request):
    company = get_current_company(request)

    # 詳細画面アクセスをログに記録
    log_view_detail(request.user, company)

    # 管理者の場合は会社一覧を取得
    companies = None
    if request.user.is_superuser:
        companies = Company.objects.all().order_by('pk')

    # 部署一覧も取得（表示順で最新5件）
    departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id).order_by('display_order', 'name')[:5]

    # 担当者一覧も取得
    company_users = CompanyUser.objects.filter(tenant_id=company.tenant_id)

    # 担当者のうち、ログインアカウントが存在するメールアドレスのセットを取得
    user_emails = [user.email for user in company_users if user.email]
    users_with_account = set(get_user_model().objects.filter(email__in=user_emails).values_list('email', flat=True))

    # 全部署を取得し、コードをキーにした辞書を作成
    all_departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id)
    department_map = {d.department_code: d.name for d in all_departments}

    # 本日以降有効なクライアント契約を取得
    from django.utils import timezone
    from apps.contract.models import ClientContract
    today = timezone.localdate()
    
    # 各担当者に部署名とバッジ情報を追加
    for user in company_users:
        user.department_name = department_map.get(user.department_code, '未設定') # 存在しないコードの場合は'未設定'
        
        # 派遣元責任者として指定されているか確認
        user.is_responsible = ClientContract.objects.filter(
            haken_info__responsible_person_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
        
        # 派遣元苦情申出先として指定されているか確認
        user.is_complaint_officer = ClientContract.objects.filter(
            haken_info__complaint_officer_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()

    # 変更履歴を取得
    change_logs, change_logs_count = get_company_change_logs(company, limit=5)
    
    return render(request, 'company/company_detail.html', {
        'company': company,
        'companies': companies,
        'departments': departments,
        'company_users': company_users,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
        'users_with_account': users_with_account,
    })

@login_required
@permission_required('company.add_company', raise_exception=True)
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            log_model_action(request.user, 'create', company)
            messages.success(request, f'会社「{company.name}」を登録しました。')
            return redirect(reverse('company:company_detail') + f'?company_id={company.pk}')
    else:
        form = CompanyForm()

    return render(request, 'company/company_edit.html', {
        'form': form,
        'title': '新規会社登録'
    })

@login_required
@permission_required('company.change_company', raise_exception=True)
def company_edit(request, pk=None):
    company = get_current_company(request, pk=pk)

    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            # 変更があったかどうかをチェック
            if form.has_changed():
                form.save()
                log_model_action(request.user, 'update', company)
                messages.success(request, '会社情報が更新されました。')
            else:
                messages.info(request, '変更はありませんでした。')
            return redirect('company:company_detail') # 更新後、参照ページにリダイレクト
    else:
        form = CompanyForm(instance=company)

    return render(request, 'company/company_edit.html', {'form': form, 'company': company})

# 部署管理のビュー

@login_required
@permission_required('company.view_companydepartment', raise_exception=True)
def department_detail(request, pk):
    company = get_current_company(request)
    department = get_object_or_404(CompanyDepartment, pk=pk)
    log_view_detail(request.user, department)
    
    # この会社の全部署一覧を取得
    departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id).order_by('display_order', 'name')
    
    return render(request, 'company/company_department_detail.html', {
        'department': department,
        'departments': departments,
        'current_department': department,
        'company': company,
    })

@login_required
@permission_required('company.add_companydepartment', raise_exception=True)
def department_create(request):
    company = get_current_company(request)
    if request.method == 'POST':
        form = CompanyDepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.tenant_id = company.tenant_id
            department.corporate_number = company.corporate_number
            department.save()
            log_model_action(request.user, 'create', department)
            messages.success(request, '部署が作成されました。')
            return redirect('company:company_detail')
    else:
        form = CompanyDepartmentForm(initial={'corporate_number': company.corporate_number})
    
    departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id).order_by('display_order', 'name')

    return render(request, 'company/company_department_form.html', {
        'form': form,
        'title': '部署作成',
        'departments': departments,
        'company': company,
    })

@login_required
@permission_required('company.change_companydepartment', raise_exception=True)
def department_edit(request, pk):
    company = get_current_company(request)
    department = get_object_or_404(CompanyDepartment, pk=pk)
    if request.method == 'POST':
        form = CompanyDepartmentForm(request.POST, instance=department)
        if form.is_valid():
            # 変更があったかどうかをチェック
            if form.has_changed():
                form.save()
                log_model_action(request.user, 'update', department)
                messages.success(request, '部署情報が更新されました。')
            else:
                messages.info(request, '変更はありませんでした。')
            return redirect('company:department_detail', pk=department.pk)
    else:
        form = CompanyDepartmentForm(instance=department)
    
    # この会社の全部署一覧を取得
    departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id).order_by('display_order', 'name')
    
    return render(request, 'company/company_department_form.html', {
        'form': form, 
        'department': department, 
        'title': '部署編集',
        'departments': departments,
        'current_department': department,
        'company': company,
    })

@login_required
@permission_required('company.delete_companydepartment', raise_exception=True)
def department_delete(request, pk):
    company = get_current_company(request)
    department = get_object_or_404(CompanyDepartment, pk=pk)
    if request.method == 'POST':
        log_model_action(request.user, 'delete', department)
        department.delete()
        messages.success(request, '部署が削除されました。')
        return redirect('company:company_detail')
    
    return render(request, 'company/company_department_confirm_delete.html', {
        'department': department,
        'company': company,
    })

@login_required
@permission_required('company.view_company', raise_exception=True)
def change_history_list(request):
    """会社、部署、担当者の変更履歴一覧"""
    company = get_current_company(request)

    # 全てのログを統合してタイムスタンプ順にソート
    all_logs, _ = get_company_change_logs(company)

    # ページネーション
    paginator = Paginator(all_logs, 20) # 1ページあたり20件
    page = request.GET.get('page')
    change_logs = paginator.get_page(page)

    context = {
        'company': company,
        'change_logs': change_logs,
        'info_card_path': 'company/_company_info_card.html',
        'page_title': '会社関連 変更履歴一覧',
        'back_url_name': 'company:company_detail',
        # 'object' は company_detail が pk を取らないため設定しない
    }
    return render(request, 'common/common_change_history_list.html', context)


# Company User CRUD
@login_required
@permission_required('company.add_companyuser', raise_exception=True)
def company_user_create(request):
    company = get_current_company(request)

    if request.method == 'POST':
        form = CompanyUserForm(request.POST, corporate_number=company.corporate_number)
        if form.is_valid():
            company_user = form.save(commit=False)
            company_user.tenant_id = company.tenant_id
            company_user.corporate_number = company.corporate_number
            company_user.save()
            log_model_action(request.user, 'create', company_user)
            messages.success(request, '担当者を作成しました。')
            return redirect('company:company_detail')
    else:
        form = CompanyUserForm(corporate_number=company.corporate_number)

    # 担当者一覧を取得し、バッジ情報と部署情報を追加
    company_users = CompanyUser.objects.filter(tenant_id=company.tenant_id)
    
    # 本日以降有効なクライアント契約を取得
    from django.utils import timezone
    from apps.contract.models import ClientContract
    today = timezone.localdate()
    
    # 全部署を取得し、コードをキーにした辞書を作成
    all_departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id)
    department_map = {d.department_code: d.name for d in all_departments}
    
    # 各担当者に部署名とバッジ情報を追加
    for user in company_users:
        user.department_name = department_map.get(user.department_code, '未設定')
        
        # 派遣元責任者として指定されているか確認
        user.is_responsible = ClientContract.objects.filter(
            haken_info__responsible_person_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
        
        # 派遣元苦情申出先として指定されているか確認
        user.is_complaint_officer = ClientContract.objects.filter(
            haken_info__complaint_officer_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
    
    return render(request, 'company/company_user_form.html', {
        'form': form,
        'company': company,
        'title': '担当者作成',
        'company_users': company_users
    })

@login_required
@permission_required('company.change_companyuser', raise_exception=True)
def company_user_edit(request, pk):
    company = get_current_company(request)
    company_user = get_object_or_404(CompanyUser, pk=pk)

    if request.method == 'POST':
        form = CompanyUserForm(request.POST, instance=company_user, corporate_number=company.corporate_number)
        if form.is_valid():
            form.save()
            log_model_action(request.user, 'update', company_user)
            messages.success(request, '担当者情報を更新しました。')
            return redirect('company:company_detail')
    else:
        form = CompanyUserForm(instance=company_user, corporate_number=company.corporate_number)

    # 担当者一覧を取得し、バッジ情報と部署情報を追加
    company_users = CompanyUser.objects.filter(tenant_id=company.tenant_id)
    
    # 本日以降有効なクライアント契約を取得
    from django.utils import timezone
    from apps.contract.models import ClientContract
    today = timezone.localdate()
    
    # 全部署を取得し、コードをキーにした辞書を作成
    all_departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id)
    department_map = {d.department_code: d.name for d in all_departments}
    
    # 各担当者に部署名とバッジ情報を追加
    for user in company_users:
        user.department_name = department_map.get(user.department_code, '未設定')
        
        # 派遣元責任者として指定されているか確認
        user.is_responsible = ClientContract.objects.filter(
            haken_info__responsible_person_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
        
        # 派遣元苦情申出先として指定されているか確認
        user.is_complaint_officer = ClientContract.objects.filter(
            haken_info__complaint_officer_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
    
    return render(request, 'company/company_user_form.html', {
        'form': form,
        'company': company,
        'title': '担当者編集',
        'current_company_user': company_user,
        'company_users': company_users
    })

@login_required
@permission_required('company.delete_companyuser', raise_exception=True)
def company_user_delete(request, pk):
    company = get_current_company(request)
    company_user = get_object_or_404(CompanyUser, pk=pk)
    if request.method == 'POST':
        log_model_action(request.user, 'delete', company_user)
        company_user.delete()
        messages.success(request, '担当者を削除しました。')
        return redirect('company:company_detail')

    # 担当者一覧を取得し、バッジ情報と部署情報を追加
    company_users = CompanyUser.objects.filter(tenant_id=company.tenant_id)
    
    # 本日以降有効なクライアント契約を取得
    from django.utils import timezone
    from apps.contract.models import ClientContract
    today = timezone.localdate()
    
    # 全部署を取得し、コードをキーにした辞書を作成
    all_departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id)
    department_map = {d.department_code: d.name for d in all_departments}
    
    # 各担当者に部署名とバッジ情報を追加
    for user in company_users:
        user.department_name = department_map.get(user.department_code, '未設定')
        
        # 派遣元責任者として指定されているか確認
        user.is_responsible = ClientContract.objects.filter(
            haken_info__responsible_person_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
        
        # 派遣元苦情申出先として指定されているか確認
        user.is_complaint_officer = ClientContract.objects.filter(
            haken_info__complaint_officer_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
    
    return render(request, 'company/company_user_confirm_delete.html', {
        'company_user': company_user,
        'company': company,
        'company_users': company_users,
        'current_company_user': company_user,
    })


@login_required
@permission_required('company.view_companyuser', raise_exception=True)
def company_user_detail(request, pk):
    from django.utils import timezone
    from apps.contract.models import ClientContract
    User = get_user_model()
    
    company = get_current_company(request)
    company_user = get_object_or_404(CompanyUser, pk=pk)
    log_view_detail(request.user, company_user)
    company_users = CompanyUser.objects.filter(tenant_id=company.tenant_id)

    # 担当者のうち、ログインアカウントが存在するメールアドレスのセットを取得
    user_emails = [user.email for user in company_users if user.email]
    users_with_account = set(User.objects.filter(email__in=user_emails).values_list('email', flat=True))

    # ログインアカウントの存在確認
    user_account = None
    if company_user.email:
        user_account = User.objects.filter(email=company_user.email).first()

    if request.method == 'POST' and 'toggle_account' in request.POST:
        if not request.user.has_perm('company.change_companyuser'):
            messages.error(request, '権限がありません。')
            return redirect('company:company_user_detail', pk=pk)

        if not company_user.email:
            messages.error(request, 'メールアドレスが設定されていないため、アカウント操作はできません。')
            return redirect('company:company_user_detail', pk=pk)

        if user_account:
            # アカウント削除
            user_account.delete()
            log_model_action(request.user, 'delete', user_account)
            messages.success(request, f'ユーザーアカウント「{company_user.email}」を削除しました。')
        else:
            # アカウント作成
            if User.objects.filter(email=company_user.email).exists():
                messages.error(request, 'このメールアドレスは既に使用されています。')
                return redirect('company:company_user_detail', pk=pk)

            user_account = User.objects.create_user(
                username=company_user.email,
                email=company_user.email,
                last_name=company_user.name_last,
                first_name=company_user.name_first,
                tenant_id=company.tenant_id
            )
            # companyグループに追加
            try:
                company_group = Group.objects.get(name='company')
                user_account.groups.add(company_group)
            except Group.DoesNotExist:
                messages.warning(request, '「company」グループが存在しません。権限が正しく付与されませんでした。')

            log_model_action(request.user, 'create', user_account)
            messages.success(request, f'ユーザーアカウント「{company_user.email}」を作成しました。')

        return redirect('company:company_user_detail', pk=pk)

    # 全部署を取得し、コードをキーにした辞書を作成
    all_departments = CompanyDepartment.objects.filter(tenant_id=company.tenant_id)
    department_map = {d.department_code: d.name for d in all_departments}

    # 本日以降有効なクライアント契約を取得
    today = timezone.localdate()
    
    # 各担当者に部署名とバッジ情報を追加
    for user in company_users:
        user.department_name = department_map.get(user.department_code, '未設定')
        
        # 派遣元責任者として指定されているか確認
        user.is_responsible = ClientContract.objects.filter(
            haken_info__responsible_person_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
        
        # 派遣元苦情申出先として指定されているか確認
        user.is_complaint_officer = ClientContract.objects.filter(
            haken_info__complaint_officer_company=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()

    # 担当者の部署情報を取得
    department = None
    if company_user.department_code:
        try:
            department = CompanyDepartment.objects.get(
                tenant_id=company.tenant_id,
                department_code=company_user.department_code
            )
        except CompanyDepartment.DoesNotExist:
            # 部署が存在しない場合
            pass
    
    # 派遣元責任者または派遣元苦情申出先として指定されているクライアント契約を統合取得
    related_contracts = ClientContract.objects.filter(
        Q(haken_info__responsible_person_company=company_user) |
        Q(haken_info__complaint_officer_company=company_user),
        start_date__lte=today,
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).select_related('client', 'haken_info').distinct().order_by('start_date')

    # 各契約に役割情報を追加
    for contract in related_contracts:
        contract.is_responsible_role = (contract.haken_info.responsible_person_company == company_user)
        contract.is_complaint_role = (contract.haken_info.complaint_officer_company == company_user)

    return render(request, 'company/company_user_detail.html', {
        'object': company_user,
        'company_users': company_users,
        'current_company_user': company_user,
        'company': company,
        'department': department,
        'related_contracts': related_contracts,
        'user_account': user_account,
        'users_with_account': users_with_account,
    })

@login_required
@permission_required('company.change_company', raise_exception=True)
def company_seal_upload(request):
    """会社印（丸印・角印）のアップロード処理"""
    company = get_current_company(request)

    if request.method == 'POST':
        form = CompanySealUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data['seal_image']
            seal_type = form.cleaned_data['seal_type'] # 'round' or 'square'
            x = form.cleaned_data.get('crop_x')
            y = form.cleaned_data.get('crop_y')
            w = form.cleaned_data.get('crop_width')
            h = form.cleaned_data.get('crop_height')

            try:
                with Image.open(image) as img:
                    orig_w, orig_h = img.size

                    # クロップ処理
                    if all(v is not None for v in [x, y, w, h]):
                        left = max(0, int(float(x)))
                        top = max(0, int(float(y)))
                        right = min(orig_w, int(float(x + w)))
                        bottom = min(orig_h, int(float(y + h)))
                        
                        if right > left and bottom > top:
                            img = img.crop((left, top, right, bottom))

                    # RGBA（透明度あり）は維持しつつ、それ以外はRGBにする
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                    
                    # 600x600にリサイズ
                    img = img.resize((600, 600), Image.Resampling.LANCZOS)
                    
                    # メモリ上に保存
                    temp_io = BytesIO()
                    img.save(temp_io, format='PNG')
                    image_content = ContentFile(temp_io.getvalue())
                    
                    # 保存処理
                    company._upload_type = f"{seal_type}_seal"
                    if seal_type == 'round':
                        company.round_seal.save(f'round_seal.png', image_content, save=True)
                    else:
                        company.square_seal.save(f'square_seal.png', image_content, save=True)
                
                log_model_action(request.user, 'update', company)
                messages.success(request, f'{"丸印" if seal_type == "round" else "角印"}を登録しました。')
            except Exception as e:
                messages.error(request, f'画像の保存中にエラーが発生しました: {e}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

    return redirect('company:company_detail')

@login_required
@permission_required('company.change_company', raise_exception=True)
def company_seal_delete(request):
    """会社印（丸印・角印）の削除処理"""
    company = get_current_company(request)

    if request.method == 'POST':
        seal_type = request.POST.get('seal_type')
        if seal_type == 'round':
            if company.round_seal:
                company.round_seal.delete()
                messages.success(request, '丸印を削除しました。')
        elif seal_type == 'square':
            if company.square_seal:
                company.square_seal.delete()
                messages.success(request, '角印を削除しました。')
        
        log_model_action(request.user, 'update', company)
    
    return redirect('company:company_detail')

@login_required
@permission_required('company.view_company', raise_exception=True)
def serve_company_seal(request, seal_type):
    """会社印（丸印・角印）を安全に配信するビュー"""
    company = get_current_company(request)

    image_field = None
    if seal_type == 'round':
        image_field = company.round_seal
    elif seal_type == 'square':
        image_field = company.square_seal
    else:
        raise Http404("無効な印章タイプです。")

    if not image_field:
        raise Http404("画像が見つかりません。")

    try:
        # ストレージからファイルを開く
        image_data = image_field.read()
        content_type = 'image/png'  # アップロード時にPNGに変換しているため
        return HttpResponse(image_data, content_type=content_type)
    except IOError:
        raise Http404("画像ファイルを開けませんでした。")
