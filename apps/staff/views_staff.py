import os
import logging
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.contrib import messages
from apps.system.logs.utils import log_model_action
from .forms_mail import ConnectionRequestMailForm, DisconnectionMailForm

from .models import Staff, StaffContacted, StaffContactSchedule, StaffQualification, StaffSkill, StaffFile, StaffMynumber, StaffBank, StaffInternational, StaffDisability, StaffContact, StaffFavorite
from .forms import StaffForm, StaffContactedForm, StaffContactScheduleForm, StaffFileForm, StaffFaceUploadForm, StaffTagEditForm
from .utils import get_staff_face_photo_style, delete_staff_placeholder
from apps.system.settings.models import Dropdowns
from apps.system.logs.models import AppLog
from apps.common.utils import fill_excel_from_template
from apps.common.constants import Constants
from django.http import HttpResponse
from .resources import StaffResource
import datetime
from django.utils import timezone

# ロガーの作成
logger = logging.getLogger('staff')


@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_export(request):
    """スタッフデータのエクスポート（CSV/Excel）"""
    # フィルタリングロジックをstaff_listからコピー
    query = request.GET.get('q', '').strip()
    staff_regist_status_filter = request.GET.get('regist_status', '').strip()
    department_filter = request.GET.get('department', '').strip()
    employment_type_filter = request.GET.get('employment_type', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    has_request_filter = request.GET.get('has_request', '')
    has_international_filter = request.GET.get('has_international', '')
    has_disability_filter = request.GET.get('has_disability', '')
    format_type = request.GET.get('format', 'csv')

    staffs = Staff.objects.all()

    if has_request_filter == 'true':
        from apps.connect.models import (
            ConnectStaff, MynumberRequest, ProfileRequest, BankRequest,
            ContactRequest, ConnectInternationalRequest, DisabilityRequest
        )
        pending_mynumber_cs_ids = MynumberRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_profile_cs_ids = ProfileRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_bank_cs_ids = BankRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_contact_cs_ids = ContactRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_international_cs_ids = ConnectInternationalRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_disability_cs_ids = DisabilityRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)

        all_pending_cs_ids = set()
        all_pending_cs_ids.update(pending_mynumber_cs_ids)
        all_pending_cs_ids.update(pending_profile_cs_ids)
        all_pending_cs_ids.update(pending_bank_cs_ids)
        all_pending_cs_ids.update(pending_contact_cs_ids)
        all_pending_cs_ids.update(pending_international_cs_ids)
        all_pending_cs_ids.update(pending_disability_cs_ids)

        pending_emails = ConnectStaff.objects.filter(id__in=list(all_pending_cs_ids)).values_list('email', flat=True)
        staffs = staffs.filter(email__in=pending_emails)

    if query:
        staffs = staffs.filter(
            Q(name_last__icontains=query) | Q(name_first__icontains=query) |
            Q(name_kana_last__icontains=query) | Q(name_kana_first__icontains=query) |
            Q(name__icontains=query) | Q(address_kana__icontains=query) |
            Q(address1__icontains=query) | Q(address2__icontains=query) |
            Q(address3__icontains=query) | Q(email__icontains=query) |
            Q(employee_no__icontains=query)
        )

    if staff_regist_status_filter:
        staffs = staffs.filter(regist_status_id=staff_regist_status_filter)
    if department_filter:
        staffs = staffs.filter(department_code=department_filter)
    if employment_type_filter:
        staffs = staffs.filter(employment_type=employment_type_filter)
    if tag_filter:
        staffs = staffs.filter(tags=tag_filter)
    if has_international_filter:
        staffs = staffs.filter(international__isnull=False)
    if has_disability_filter:
        staffs = staffs.filter(disability__isnull=False)

    staffs = staffs.order_by('employee_no')

    # リソースを使ってエクスポート
    resource = StaffResource()
    dataset = resource.export(staffs)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    if format_type == 'excel':
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="staff_{timestamp}.xlsx"'
    else:
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="staff_{timestamp}.csv"'

    return response

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_change_history_list(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    # スタッフ、資格、技能、ファイルの変更履歴を含む
    from django.db import models as django_models

    # 関連オブジェクトのIDリストを取得
    qualification_ids = list(staff.qualifications.values_list('pk', flat=True))
    skill_ids = list(staff.skills.values_list('pk', flat=True))
    file_ids = list(staff.files.values_list('pk', flat=True))

    grade_ids = list(staff.grades.values_list('pk', flat=True))

    # 1対1の関連オブジェクトのIDを取得（存在する場合）
    mynumber_id = getattr(staff, 'mynumber', None) and staff.mynumber.pk
    contact_id = getattr(staff, 'contact', None) and staff.contact.pk
    bank_id = getattr(staff, 'bank', None) and staff.bank.pk
    international_id = getattr(staff, 'international', None) and staff.international.pk
    disability_id = getattr(staff, 'disability', None) and staff.disability.pk
    payroll_id = getattr(staff, 'payroll', None) and staff.payroll.pk

    # 削除されたオブジェクトのIDを取得するために、スタッフ名を含む削除ログから object_id を抽出
    deleted_object_ids = {}
    for model_name in ['StaffQualification', 'StaffSkill', 'StaffFile', 'StaffGrade', 'StaffMynumber', 
                       'StaffContact', 'StaffBank', 'StaffInternational', 'StaffDisability', 'StaffPayroll']:
        deleted_logs = AppLog.objects.filter(
            model_name=model_name,
            object_repr__icontains=str(staff),
            action='delete'
        ).values_list('object_id', flat=True)
        if deleted_logs:
            deleted_object_ids[model_name] = list(deleted_logs)
    
    # 現在存在するオブジェクトのIDと削除されたオブジェクトのIDを統合
    all_qualification_ids = [str(pk) for pk in qualification_ids] + deleted_object_ids.get('StaffQualification', [])
    all_skill_ids = [str(pk) for pk in skill_ids] + deleted_object_ids.get('StaffSkill', [])
    all_file_ids = [str(pk) for pk in file_ids] + deleted_object_ids.get('StaffFile', [])
    all_grade_ids = [str(pk) for pk in grade_ids] + deleted_object_ids.get('StaffGrade', [])
    all_mynumber_ids = ([str(mynumber_id)] if mynumber_id else []) + deleted_object_ids.get('StaffMynumber', [])
    all_contact_ids = ([str(contact_id)] if contact_id else []) + deleted_object_ids.get('StaffContact', [])
    all_bank_ids = ([str(bank_id)] if bank_id else []) + deleted_object_ids.get('StaffBank', [])
    all_international_ids = ([str(international_id)] if international_id else []) + deleted_object_ids.get('StaffInternational', [])
    all_disability_ids = ([str(disability_id)] if disability_id else []) + deleted_object_ids.get('StaffDisability', [])
    all_payroll_ids = ([str(payroll_id)] if payroll_id else []) + deleted_object_ids.get('StaffPayroll', [])
    
    all_logs = AppLog.objects.filter(
        django_models.Q(model_name='Staff', object_id=str(staff.pk)) |
        django_models.Q(model_name='StaffQualification', object_id__in=all_qualification_ids) |
        django_models.Q(model_name='StaffSkill', object_id__in=all_skill_ids) |
        django_models.Q(model_name='StaffFile', object_id__in=all_file_ids) |
        django_models.Q(model_name='StaffGrade', object_id__in=all_grade_ids) |
        django_models.Q(model_name='StaffMynumber', object_id__in=all_mynumber_ids) |
        django_models.Q(model_name='StaffContact', object_id__in=all_contact_ids) |
        django_models.Q(model_name='StaffBank', object_id__in=all_bank_ids) |
        django_models.Q(model_name='StaffInternational', object_id__in=all_international_ids) |
        django_models.Q(model_name='StaffDisability', object_id__in=all_disability_ids) |
        django_models.Q(model_name='StaffPayroll', object_id__in=all_payroll_ids) |
        django_models.Q(model_name='ConnectStaff', object_id=str(staff.pk)),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')

    paginator = Paginator(all_logs, 20)
    page = request.GET.get('page')
    change_logs = paginator.get_page(page)

    context = {
        'object': staff,
        'staff': staff,
        'change_logs': change_logs,
        'info_card_path': 'staff/_staff_info_card.html',
        'page_title': 'スタッフ関連 変更履歴一覧',
        'back_url_name': 'staff:staff_detail',
    }
    return render(request, 'common/common_change_history_list.html', context)

@login_required
@permission_required('staff.view_staffcontacted', raise_exception=True)
def staff_contacted_detail(request, pk):
    contacted = get_object_or_404(StaffContacted, pk=pk)
    staff = contacted.staff
    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    log_view_detail(request.user, contacted)
    return render(request, 'staff/staff_contacted_detail.html', {'contacted': contacted, 'staff': staff})

# 連絡履歴 削除
@login_required
@permission_required('staff.delete_staffcontacted', raise_exception=True)
def staff_contacted_delete(request, pk):
    contacted = get_object_or_404(StaffContacted, pk=pk)
    staff = contacted.staff
    if request.method == 'POST':
        contacted.delete()
        return redirect('staff:staff_detail', pk=staff.pk)
    return render(request, 'staff/staff_contacted_confirm_delete.html', {'contacted': contacted, 'staff': staff})

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_list(request):
    from .utils import get_annotated_staff_queryset, annotate_staff_connection_info
    staff_face_photo_style = get_staff_face_photo_style()
    sort = request.GET.get('sort', 'pk')  # デフォルトソートをpkに設定
    query = request.GET.get('q', '').strip()
    staff_regist_status_filter = request.GET.get('regist_status', '').strip()  # 登録区分フィルター
    department_filter = request.GET.get('department', '').strip()  # 所属部署フィルター
    employment_type_filter = request.GET.get('employment_type', '').strip()  # 雇用形態フィルター
    tag_filter = request.GET.get('tag', '').strip()  # タグフィルター
    has_request_filter = request.GET.get('has_request', '')
    has_international_filter = request.GET.get('has_international', '')
    has_disability_filter = request.GET.get('has_disability', '')
    is_registration_status_view = request.GET.get('registration_status', '') == 'true'

    # 基本のクエリセット
    staffs = get_annotated_staff_queryset(request.user).prefetch_related('tags')

    # 社員登録状況一覧の場合
    if is_registration_status_view:
        staffs = staffs.exclude(employee_no__isnull=True).exclude(employee_no='')

    if has_request_filter == 'true':
        from apps.connect.models import (
            ConnectStaff, MynumberRequest, ProfileRequest, BankRequest,
            ContactRequest, ConnectInternationalRequest, DisabilityRequest
        )
        # Get all ConnectStaff ids that have pending requests
        pending_mynumber_cs_ids = MynumberRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_profile_cs_ids = ProfileRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_bank_cs_ids = BankRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_contact_cs_ids = ContactRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_international_cs_ids = ConnectInternationalRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
        pending_disability_cs_ids = DisabilityRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)

        all_pending_cs_ids = set()
        all_pending_cs_ids.update(pending_mynumber_cs_ids)
        all_pending_cs_ids.update(pending_profile_cs_ids)
        all_pending_cs_ids.update(pending_bank_cs_ids)
        all_pending_cs_ids.update(pending_contact_cs_ids)
        all_pending_cs_ids.update(pending_international_cs_ids)
        all_pending_cs_ids.update(pending_disability_cs_ids)

        # Get the emails of these ConnectStaff objects
        pending_emails = ConnectStaff.objects.filter(id__in=list(all_pending_cs_ids)).values_list('email', flat=True)

        # Filter the staffs
        staffs = staffs.filter(email__in=pending_emails)

    # 会社の法人番号を取得（最初の会社を仮定）
    from apps.company.models import Company
    company = Company.objects.first()
    corporate_number = company.corporate_number if company else None

    # キーワード検索
    if query:
        if query.startswith('contact_date:'):
            date_str = query.replace('contact_date:', '')
            staff_ids = StaffContactSchedule.objects.filter(contact_date=date_str).values_list('staff_id', flat=True)
            staffs = staffs.filter(id__in=staff_ids)
        elif query.startswith('contact_date_before:'):
            date_str = query.replace('contact_date_before:', '')
            staff_ids = StaffContactSchedule.objects.filter(contact_date__lt=date_str).values_list('staff_id', flat=True)
            staffs = staffs.filter(id__in=staff_ids)
        else:
            staffs = staffs.filter(
                Q(name_last__icontains=query)
                |Q(name_first__icontains=query)
                |Q(name_kana_last__icontains=query)
                |Q(name_kana_first__icontains=query)
                |Q(name__icontains=query)
                |Q(address_kana__icontains=query)
                |Q(address1__icontains=query)
                |Q(address2__icontains=query)
                |Q(address3__icontains=query)
                |Q(email__icontains=query)
                |Q(employee_no__icontains=query)
            )

    # 登録区分での絞り込み
    if staff_regist_status_filter:
        staffs = staffs.filter(regist_status_id=staff_regist_status_filter)
    # 所属部署での絞り込み
    if department_filter:
        staffs = staffs.filter(department_code=department_filter)
    # 雇用形態での絞り込み
    if employment_type_filter:
        staffs = staffs.filter(employment_type=employment_type_filter)

    # タグでの絞り込み
    if tag_filter:
        staffs = staffs.filter(tags=tag_filter)

    # 外国籍での絞り込み
    if has_international_filter:
        staffs = staffs.filter(international__isnull=False)

    # 障害者での絞り込み
    if has_disability_filter:
        staffs = staffs.filter(disability__isnull=False)

    # ソート可能なフィールドを定義
    sortable_fields = [
        'employee_no', '-employee_no',
        'name_last', '-name_last',
        'name_first', '-name_first',
        'email', '-email',
        'address1', '-address1',
        'age', '-age',
        'pk', '-pk',
    ]

    if sort in sortable_fields:
        staffs = staffs.order_by(sort)
    else:
        staffs = staffs.order_by('pk') # 不正なソート指定の場合はpkでソート

    # 登録区分の選択肢を取得
    from apps.master.models import StaffRegistStatus
    staff_regist_status_options = StaffRegistStatus.objects.filter(is_active=True).order_by('display_order')
    # 各オプションに選択状態を追加
    for option in staff_regist_status_options:
        option.is_selected = (staff_regist_status_filter == str(option.pk))

    # 雇用形態の選択肢を取得
    from apps.master.models import EmploymentType
    employment_type_options = EmploymentType.objects.filter(is_active=True).order_by('display_order', 'name')
    for option in employment_type_options:
        option.is_selected = (employment_type_filter == str(option.pk))

    # タグの選択肢を取得
    from apps.master.models import StaffTag
    staff_tag_options = StaffTag.objects.filter(is_active=True).order_by('display_order', 'name')
    for option in staff_tag_options:
        option.is_selected = (tag_filter == str(option.pk))

    # 所属部署の選択肢を取得（現在有効な部署のみ）
    from apps.company.models import CompanyDepartment

    current_date = timezone.localdate()
    department_options = CompanyDepartment.get_valid_departments(current_date)

    # 各部署オプションに選択状態を追加
    for dept in department_options:
        dept.is_selected = (department_filter == dept.department_code)

    paginator = Paginator(staffs, 10)  # 1ページあたり10件表示
    page_number = request.GET.get('page')  # URLからページ番号を取得
    staffs_pages = paginator.get_page(page_number)

    # 各スタッフの接続情報などを効率的に取得
    annotate_staff_connection_info(staffs_pages)

    return render(request, 'staff/staff_list.html', {
        'staffs': staffs_pages,
        'query': query,
        'sort': sort,
        'regist_status_filter': staff_regist_status_filter,
        'staff_regist_status_options': staff_regist_status_options,
        'department_filter': department_filter,
        'department_options': department_options,
        'employment_type_filter': employment_type_filter,
        'employment_type_options': employment_type_options,
        'tag_filter': tag_filter,
        'staff_tag_options': staff_tag_options,
        'has_request_filter': has_request_filter,
        'has_international_filter': has_international_filter,
        'has_disability_filter': has_disability_filter,
        'staff_face_photo_style': staff_face_photo_style,
        'is_registration_status_view': is_registration_status_view,
    })

@login_required
@permission_required('staff.add_staff', raise_exception=True)
def staff_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save()
            messages.success(request, f'スタッフ「{staff.name}」を作成しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffForm()
    return render(request, 'staff/staff_form.html', {'form': form})

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_detail(request, pk):
    staff_face_photo_style = get_staff_face_photo_style()
    staff = get_object_or_404(Staff, pk=pk)

    # 接続依頼の切り替え処理
    if request.method == 'POST' and 'toggle_connect_request' in request.POST:
        if staff.email:
            from apps.connect.models import ConnectStaff
            from apps.company.models import Company
            try:
                # 現在のユーザーの会社の法人番号を取得
                company = Company.objects.first()  # 仮の実装、実際は適切な会社を取得
                if company and company.corporate_number:
                    connect_request, created = ConnectStaff.objects.get_or_create(
                        corporate_number=company.corporate_number,
                        email=staff.email,
                        defaults={'status': 'pending'}
                    )
                    if not created:
                        # 既存のレコードがある場合は削除（スイッチOFF）
                        connect_request.delete()
                        # メール送信
                        mail_form = DisconnectionMailForm(staff=staff, user=request.user)
                        success, message = mail_form.send_mail()
                        if success:
                            messages.success(request, f'スタッフ「{staff.name}」への接続を解除し、メールを送信しました。')
                        else:
                            messages.warning(request, f'スタッフ「{staff.name}」への接続を解除しましたが、メールの送信に失敗しました: {message}')
                        # 変更履歴に記録
                        AppLog.objects.create(
                            user=request.user,
                            model_name='ConnectStaff',
                            object_id=str(staff.pk),
                            object_repr=f'{staff} - 接続依頼取り消し',
                            action='delete'
                        )
                    else:
                        # 新規作成された場合（スイッチON）
                        # メール送信
                        mail_form = ConnectionRequestMailForm(staff=staff, user=request.user)
                        success, message = mail_form.send_mail()
                        if success:
                            messages.success(request, f'スタッフ「{staff.name}」への接続申請を送信し、メールを送信しました。')
                        else:
                            messages.warning(request, f'スタッフ「{staff.name}」への接続申請を送信しましたが、メールの送信に失敗しました: {message}')

                        # 変更履歴に記録
                        AppLog.objects.create(
                            user=request.user,
                            model_name='ConnectStaff',
                            object_id=str(staff.pk),
                            object_repr=f'{staff} - 接続依頼送信',
                            action='create'
                        )
                        # 既存ユーザーがいる場合は権限付与
                        from django.contrib.auth import get_user_model
                        from django.contrib.auth.models import Permission
                        User = get_user_model()
                        try:
                            user = User.objects.get(email=staff.email)
                            # 接続権限を付与
                            connect_permissions = Permission.objects.filter(
                                content_type__app_label='connect',
                                codename__in=['view_connectstaff', 'change_connectstaff']
                            )
                            user.user_permissions.add(*connect_permissions)
                            logger.info(f"接続依頼時に権限付与: {user.email}")
                        except User.DoesNotExist:
                            logger.info(f"接続依頼送信（未登録ユーザー）: {staff.email}")
            except Exception as e:
                messages.error(request, f'接続依頼の処理中にエラーが発生しました: {str(e)}')
        return redirect('staff:staff_detail', pk=pk)
    # 連絡履歴と予定を統合
    all_contacts = []
    
    # 最近の履歴を取得
    for c in staff.contacted_histories.all()[:10]:
        all_contacts.append({
            'type': 'history',
            'pk': c.pk,
            'contact_type': c.contact_type,
            'content': c.content,
            'created_by': c.created_by,
            'at': c.contacted_at,
            'is_schedule': False,
        })
    
    # 最近の予定を取得
    for s in staff.contact_schedules.all()[:10]:
        # DateFieldをDateTimeField的に扱ってソート可能にする
        dt = timezone.make_aware(datetime.datetime.combine(s.contact_date, datetime.time.min))
        all_contacts.append({
            'type': 'schedule',
            'pk': s.pk,
            'contact_type': s.contact_type,
            'content': s.content,
            'created_by': s.created_by,
            'at': dt, # ソート用
            'display_date': s.contact_date, # 表示用
            'is_schedule': True,
        })
    
    # 日付の降順でソート
    all_contacts.sort(key=lambda x: x['at'], reverse=True)
    contacted_combined_list = all_contacts[:5]

    # スタッフ契約（最新5件）
    from apps.contract.models import StaffContract
    staff_contracts = StaffContract.objects.filter(staff=staff).order_by('-start_date')[:5]
    staff_contracts_count = StaffContract.objects.filter(staff=staff).count()
    # 資格情報（最新5件）
    qualifications = staff.qualifications.select_related('qualification').order_by('-acquired_date')[:5]
    # 技能情報（最新5件）
    skills = staff.skills.select_related('skill').order_by('-acquired_date')[:5]
    # ファイル情報（最新5件）
    files = staff.files.order_by('-uploaded_at')[:5]
    # 評価情報（最新5件）
    evaluations = staff.evaluations.order_by('-evaluation_date')[:5]
    from django.db.models import Avg, Count
    avg_rating = staff.evaluations.aggregate(Avg('rating'))['rating__avg']
    if avg_rating:
        avg_rating = round(avg_rating, 2)
    
    # 評価分布の計算
    rating_distribution = []
    total_evaluations = staff.evaluations.count()
    if total_evaluations > 0:
        # 1〜5の各評価について集計
        for i in range(5, 0, -1):
            count = staff.evaluations.filter(rating=i).count()
            percentage = (count / total_evaluations) * 100
            rating_distribution.append({
                'rating': i,
                'count': count,
                'percentage': round(percentage, 1)
            })
    else:
        # データがない場合も空枠を表示するためにリストを作成
        for i in range(5, 0, -1):
            rating_distribution.append({
                'rating': i,
                'count': 0,
                'percentage': 0
            })


    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    log_view_detail(request.user, staff)
    # 変更履歴（AppLogから取得、最新5件）- スタッフ、資格、技能、ファイルの変更を含む
    from django.db import models as django_models

    # 現在存在する関連オブジェクトのIDリストを取得
    qualification_ids = list(staff.qualifications.values_list('pk', flat=True))
    skill_ids = list(staff.skills.values_list('pk', flat=True))
    file_ids = list(staff.files.values_list('pk', flat=True))
    flag_ids = list(staff.flags.values_list('pk', flat=True))
    grade_ids = list(staff.grades.values_list('pk', flat=True))

    # 1対1の関連オブジェクトのIDを取得（存在する場合）
    mynumber_id = getattr(staff, 'mynumber', None) and staff.mynumber.pk
    contact_id = getattr(staff, 'contact', None) and staff.contact.pk
    bank_id = getattr(staff, 'bank', None) and staff.bank.pk
    international_id = getattr(staff, 'international', None) and staff.international.pk
    disability_id = getattr(staff, 'disability', None) and staff.disability.pk
    payroll_id = getattr(staff, 'payroll', None) and staff.payroll.pk

    # スタッフに関連するすべてのログを取得（削除されたオブジェクトも含む）
    
    # 削除されたオブジェクトのIDを取得するために、スタッフ名を含む削除ログから object_id を抽出
    deleted_object_ids = {}
    for model_name in ['StaffQualification', 'StaffSkill', 'StaffFile', 'StaffFlag', 'StaffGrade', 'StaffMynumber', 
                       'StaffContact', 'StaffBank', 'StaffInternational', 'StaffDisability', 'StaffPayroll']:
        deleted_logs = AppLog.objects.filter(
            model_name=model_name,
            object_repr__icontains=str(staff),
            action='delete'
        ).values_list('object_id', flat=True)
        if deleted_logs:
            deleted_object_ids[model_name] = list(deleted_logs)
    
    # 現在存在するオブジェクトのIDと削除されたオブジェクトのIDを統合
    all_qualification_ids = [str(pk) for pk in qualification_ids] + deleted_object_ids.get('StaffQualification', [])
    all_skill_ids = [str(pk) for pk in skill_ids] + deleted_object_ids.get('StaffSkill', [])
    all_file_ids = [str(pk) for pk in file_ids] + deleted_object_ids.get('StaffFile', [])
    all_flag_ids = [str(pk) for pk in flag_ids] + deleted_object_ids.get('StaffFlag', [])
    all_grade_ids = [str(pk) for pk in grade_ids] + deleted_object_ids.get('StaffGrade', [])
    all_mynumber_ids = ([str(mynumber_id)] if mynumber_id else []) + deleted_object_ids.get('StaffMynumber', [])
    all_contact_ids = ([str(contact_id)] if contact_id else []) + deleted_object_ids.get('StaffContact', [])
    all_bank_ids = ([str(bank_id)] if bank_id else []) + deleted_object_ids.get('StaffBank', [])
    all_international_ids = ([str(international_id)] if international_id else []) + deleted_object_ids.get('StaffInternational', [])
    all_disability_ids = ([str(disability_id)] if disability_id else []) + deleted_object_ids.get('StaffDisability', [])
    all_payroll_ids = ([str(payroll_id)] if payroll_id else []) + deleted_object_ids.get('StaffPayroll', [])
    
    change_logs_query = AppLog.objects.filter(
        django_models.Q(model_name='Staff', object_id=str(staff.pk)) |
        django_models.Q(model_name='StaffQualification', object_id__in=all_qualification_ids) |
        django_models.Q(model_name='StaffSkill', object_id__in=all_skill_ids) |
        django_models.Q(model_name='StaffFile', object_id__in=all_file_ids) |
        django_models.Q(model_name='StaffFlag', object_id__in=all_flag_ids) |
        django_models.Q(model_name='StaffGrade', object_id__in=all_grade_ids) |
        django_models.Q(model_name='StaffMynumber', object_id__in=all_mynumber_ids) |
        django_models.Q(model_name='StaffContact', object_id__in=all_contact_ids) |
        django_models.Q(model_name='StaffBank', object_id__in=all_bank_ids) |
        django_models.Q(model_name='StaffInternational', object_id__in=all_international_ids) |
        django_models.Q(model_name='StaffDisability', object_id__in=all_disability_ids) |
        django_models.Q(model_name='StaffPayroll', object_id__in=all_payroll_ids) |
        django_models.Q(model_name='ConnectStaff', object_id=str(staff.pk)),
        action__in=['create', 'update', 'delete']
    )

    change_logs = change_logs_query.order_by('-timestamp')[:5]
    change_logs_count = change_logs_query.count()

    # 接続関連情報を取得
    connect_request = None
    mynumber_request = None
    profile_request = None
    international_request = None
    bank_request = None
    disability_request = None
    contact_request = None
    last_login = None  # 最終ログイン日時を初期化

    if staff.email:
        from apps.connect.models import ConnectStaff, MynumberRequest, ProfileRequest, ConnectInternationalRequest, BankRequest, DisabilityRequest, ContactRequest
        from apps.company.models import Company
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            # 現在のユーザーの会社の法人番号を取得
            company = Company.objects.first()  # 仮の実装、実際は適切な会社を取得
            if company and company.corporate_number:
                connect_request = ConnectStaff.objects.filter(
                    corporate_number=company.corporate_number,
                    email=staff.email
                ).first()

                if connect_request and connect_request.is_approved:
                    # 接続が承認されている場合、最終ログイン日時を取得
                    try:
                        user = User.objects.get(email=staff.email)
                        last_login = user.last_login
                    except User.DoesNotExist:
                        last_login = None

                    mynumber_request = MynumberRequest.objects.filter(
                        connect_staff=connect_request,
                        status='pending'
                    ).first()
                    profile_request = ProfileRequest.objects.filter(
                        connect_staff=connect_request,
                        status='pending'
                    ).first()
                    international_request = ConnectInternationalRequest.objects.filter(
                        connect_staff=connect_request,
                        status='pending'
                    ).first()
                    bank_request = BankRequest.objects.filter(
                        connect_staff=connect_request,
                        status='pending'
                    ).first()
                    disability_request = DisabilityRequest.objects.filter(
                        connect_staff=connect_request,
                        status='pending'
                    ).first()
                    contact_request = ContactRequest.objects.filter(
                        connect_staff=connect_request,
                        status='pending'
                    ).first()
        except Exception:
            pass

    # お気に入り状況の取得
    is_favorite = StaffFavorite.objects.filter(staff=staff, user=request.user).exists()

    return render(request, 'staff/staff_detail.html', {
        'staff': staff,
        'is_favorite': is_favorite,
        'contacted_combined_list': contacted_combined_list,
        'staff_contracts': staff_contracts,
        'staff_contracts_count': staff_contracts_count,
        'qualifications': qualifications,
        'skills': skills,
        'files': files,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
        'connect_request': connect_request,
        'mynumber_request': mynumber_request,
        'profile_request': profile_request,
        'international_request': international_request,
        'bank_request': bank_request,
        'disability_request': disability_request,
        'contact_request': contact_request,
        'evaluations': evaluations,
        'avg_rating': avg_rating,
        'rating_distribution': rating_distribution,
        'total_evaluations': total_evaluations,
        'last_login': last_login,
        'staff_face_photo_style': staff_face_photo_style,
    })

# 連絡履歴 登録
@login_required
@permission_required('staff.add_staffcontacted', raise_exception=True)
def staff_contacted_create(request, staff_pk):

    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        form = StaffContactedForm(request.POST)
        if form.is_valid():
            contacted = form.save(commit=False)
            contacted.staff = staff
            contacted.save()
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        # デフォルトで現在時刻を設定
        form = StaffContactedForm(initial={'contacted_at': timezone.now()})
    return render(request, 'staff/staff_contacted_form.html', {'form': form, 'staff': staff})

# 連絡履歴 一覧
@login_required
@permission_required('staff.view_staffcontacted', raise_exception=True)
def staff_contacted_list(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    contacted_qs = staff.contacted_histories.all().order_by('-contacted_at')
    paginator = Paginator(contacted_qs, 20)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    return render(request, 'staff/staff_contacted_list.html', {'staff': staff, 'logs': logs})

# 連絡履歴 編集
@login_required
@permission_required('staff.change_staffcontacted', raise_exception=True)
def staff_contacted_update(request, pk):
    contacted = get_object_or_404(StaffContacted, pk=pk)
    staff = contacted.staff
    if request.method == 'POST':
        form = StaffContactedForm(request.POST, instance=contacted)
        if form.is_valid():
            form.save()
            messages.success(request, '連絡履歴を更新しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffContactedForm(instance=contacted)
    return render(request, 'staff/staff_contacted_form.html', {'form': form, 'staff': staff, 'contacted': contacted})


# 連絡予定 登録
@login_required
@permission_required('staff.add_staffcontactschedule', raise_exception=True)
def staff_contact_schedule_create(request, staff_pk):

    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        form = StaffContactScheduleForm(request.POST)
        if form.is_valid():
            contact_schedule = form.save(commit=False)
            contact_schedule.staff = staff
            contact_schedule.save()
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffContactScheduleForm(initial={'contact_date': timezone.now()})
    return render(request, 'staff/staff_contact_schedule_form.html', {'form': form, 'staff': staff})

# 連絡予定 一覧
@login_required
@permission_required('staff.view_staffcontactschedule', raise_exception=True)
def staff_contact_schedule_list(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    contact_schedule_qs = staff.contact_schedules.all().order_by('-contact_date')
    paginator = Paginator(contact_schedule_qs, 20)
    page = request.GET.get('page')
    schedules = paginator.get_page(page)
    return render(request, 'staff/staff_contact_schedule_list.html', {'staff': staff, 'schedules': schedules})

# 連絡予定 詳細
@login_required
@permission_required('staff.view_staffcontactschedule', raise_exception=True)
def staff_contact_schedule_detail(request, pk):
    schedule = get_object_or_404(StaffContactSchedule, pk=pk)
    staff = schedule.staff

    # 自社情報を取得
    from apps.company.models import Company, CompanyUser
    try:
        company_user = CompanyUser.objects.get(email=request.user.email)
        company = Company.objects.get(corporate_number=company_user.corporate_number)
    except (CompanyUser.DoesNotExist, Company.DoesNotExist):
        company = None

    from .forms_mail import StaffMailForm

    if request.method == 'POST':
        if 'register_history' in request.POST:
            form = StaffContactedForm(request.POST)
            if form.is_valid():
                contacted = form.save(commit=False)
                contacted.staff = staff
                contacted.save()
                # 予定を削除
                schedule.delete()
                messages.success(request, '連絡履歴を登録し、対応予定を完了（削除）しました。')
                return redirect('staff:staff_detail', pk=staff.pk)
            # バリデーションエラー時はmail_formを初期化
            mail_form = StaffMailForm(staff=staff, user=request.user, company=company)
        elif 'send_mail' in request.POST:
            mail_form = StaffMailForm(staff=staff, user=request.user, company=company, data=request.POST)
            if mail_form.is_valid():
                success, message = mail_form.send_mail()
                if success:
                    # 予定を削除
                    schedule.delete()
                    messages.success(request, f'{message} および連絡予定を完了（削除）しました。')
                    return redirect('staff:staff_detail', pk=staff.pk)
                else:
                    messages.error(request, message)
            # バリデーションエラー時はformを初期化
            initial_data = {
                'contact_type': schedule.contact_type,
                'content': schedule.content,
                'detail': schedule.detail,
                'contacted_at': timezone.now()
            }
            form = StaffContactedForm(initial=initial_data)
        else:
            # 他のPOST（基本的には無いはずだが安全のため）
            return redirect('staff:staff_contact_schedule_detail', pk=pk)
    else:
        # 予定の内容を初期値としてセット
        initial_data = {
            'contact_type': schedule.contact_type,
            'content': schedule.content,
            'detail': schedule.detail,
            'contacted_at': timezone.now()
        }
        form = StaffContactedForm(initial=initial_data)

        # メール初期値
        initial_mail_data = {
            'subject': f"ご連絡: {schedule.content}",
            'body': schedule.detail if schedule.detail else "",
            'to_email': staff.email
        }
        mail_form = StaffMailForm(staff=staff, user=request.user, company=company, initial=initial_mail_data)

    from apps.system.logs.utils import log_view_detail
    log_view_detail(request.user, schedule)
    return render(request, 'staff/staff_contact_schedule_detail.html', {
        'schedule': schedule,
        'staff': staff,
        'form': form,
        'mail_form': mail_form
    })

# 連絡予定 編集
@login_required
@permission_required('staff.change_staffcontactschedule', raise_exception=True)
def staff_contact_schedule_update(request, pk):
    schedule = get_object_or_404(StaffContactSchedule, pk=pk)
    staff = schedule.staff
    if request.method == 'POST':
        form = StaffContactScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, '連絡予定を更新しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffContactScheduleForm(instance=schedule)
    return render(request, 'staff/staff_contact_schedule_form.html', {'form': form, 'staff': staff, 'schedule': schedule})

# 連絡予定 削除
@login_required
@permission_required('staff.delete_staffcontactschedule', raise_exception=True)
def staff_contact_schedule_delete(request, pk):
    schedule = get_object_or_404(StaffContactSchedule, pk=pk)
    staff = schedule.staff
    if request.method == 'POST':
        schedule.delete()
        return redirect('staff:staff_detail', pk=staff.pk)
    return render(request, 'staff/staff_contact_schedule_confirm_delete.html', {'schedule': schedule, 'staff': staff})


@login_required
@permission_required('staff.change_staff', raise_exception=True)
def staff_update(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            # 変更があったかどうかをチェック
            if form.has_changed():
                form.save()
                delete_staff_placeholder(staff.pk)
                messages.success(request, f'スタッフ「{staff.name}」を更新しました。')
            else:
                messages.info(request, '変更はありませんでした。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffForm(instance=staff)
    return render(request, 'staff/staff_form.html', {'form': form})

@login_required
@permission_required('staff.delete_staff', raise_exception=True)
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        staff_name = staff.name
        staff.delete()
        messages.success(request, f'スタッフ「{staff_name}」を削除しました。')
        return redirect('staff:staff_list')
    return render(request, 'staff/staff_confirm_delete.html', {'staff': staff})

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_face(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    
    # 1. アップロードされた画像があるか確認
    image_path = os.path.join(settings.MEDIA_ROOT, 'staff_files', str(staff.pk) + ".jpg")
    if os.path.exists(image_path):
        return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')

    # 2. キャッシュされたプレースホルダーがあるか確認
    placeholder_dir = os.path.join(settings.MEDIA_ROOT, 'staff_files', 'placeholders')
    placeholder_path = os.path.join(placeholder_dir, str(staff.pk) + ".jpg")
    
    if os.path.exists(placeholder_path):
        return FileResponse(open(placeholder_path, 'rb'), content_type='image/jpeg')

    # 3. 画像が存在しない場合、名前を使って画像を生成
    image = Image.new("RGB", (200, 200), (200, 200, 200))  # 背景色の指定
    if staff.sex == int(Constants.SEX.MALE):
        image = Image.new("RGB", (200, 200), (140, 140, 240))  # 淡い青
    elif staff.sex == int(Constants.SEX.FEMALE):
        image = Image.new("RGB", (200, 200), (240, 140, 140))  # 淡い赤

    draw = ImageDraw.Draw(image)

    # 日本語フォントの設定
    font_path = os.path.join(settings.BASE_DIR, 'statics/fonts/ipagp.ttf')
    try:
        font = ImageFont.truetype(font_path, 80)
    except IOError:
        logger.error(f"Font not found: {font_path}")
        # フォントがない場合は標準フォントを使用
        font = ImageFont.load_default()

    # 名前を中央に描画
    if staff.name_last and staff.name_first:
        initials = f"{staff.name_last[0]}{staff.name_first[0]}"
    else:
        initials = staff.initials  # モデルのプロパティを使用

    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((200 - text_width) // 2, (200 - text_height - 20) // 2)
    draw.text(position, initials, fill="white", font=font)

    # プレースホルダーをキャッシュに保存
    try:
        os.makedirs(placeholder_dir, exist_ok=True)
        image.save(placeholder_path, "JPEG")
    except Exception as e:
        logger.error(f"Failed to save placeholder: {e}")

    # 画像をHTTPレスポンスとして返す
    response = HttpResponse(content_type="image/jpeg")
    image.save(response, "JPEG")
    return response

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_rirekisho(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    sex_dropdown = Dropdowns.objects.filter(category='sex', value=staff.sex, active=True).first()

    named_fields = {
        'name': (staff.name_last + " " + staff.name_first),
        'name_kana': (staff.name_kana_last + " " + staff.name_kana_first),
        'address_kana': (staff.address_kana),
        'address': (staff.address1 +  staff.address2 +  staff.address3),
        'phone': (staff.phone),
        'zipcode': (staff.postal_code),
        'sex': sex_dropdown.name if sex_dropdown else staff.sex,  # ここでsex_dropdownの値を設定
    }

    # レスポンスの設定
    response = HttpResponse(
        fill_excel_from_template('templates/excels/rirekisyo_a4_mhlw_DJ.xlsx', named_fields),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="staff_rirekisho_'+str(pk)+'.xlsx"'
    return response

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_kyushoku(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    sex_dropdown = Dropdowns.objects.filter(category='sex', value=staff.sex, active=True).first()

    named_fields = {
        'name': (staff.name_last + " " + staff.name_first),
        'address': (staff.address1 +  staff.address2 +  staff.address3),
        'phone': (staff.phone),
        'sex': sex_dropdown.name if sex_dropdown else staff.sex,  # ここでsex_dropdownの値を設定
    }

    # レスポンスの設定
    response = HttpResponse(
        fill_excel_from_template('templates/excels/001264775_DJ.xlsx', named_fields),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="staff_kyushoku_'+str(pk)+'.xlsx"'
    return response

# @login_required
# @permission_required('staff.view_staff', raise_exception=True)
# def staff_fuyokojo(request, pk):
#     staff = Staff.objects.get(pk=pk)
#     sex_dropdown = Dropdowns.objects.filter(category='sex', value=staff.sex, active=True).first()

#     # フォームに埋め込むデータを準備
#     form_data = {
#         'Text6': staff.name_kana_last + " " + staff.name_kana_first,  # カナ名
#         'Text7': staff.name_last + " " + staff.name_first,  # 名前
#         'Text10': staff.address1 + staff.address2 + staff.address3,  # 住所
#     }

#     # PDFフォームにデータを埋め込む（メモリ上にPDFを作成）
#     output_pdf = fill_pdf_from_template('templates/pdfs/2025bun_01_input.pdf', form_data)

#     # メモリ上のPDFをレスポンスとして返す
#     response = HttpResponse(output_pdf.read(), content_type='application/pdf')
#     response['Content-Disposition'] = 'attachment; filename="staff_fuyokojo_'+str(pk)+'.pdf"'
#     return response

# スタッフ資格登録
@login_required
@permission_required('staff.add_staffqualification', raise_exception=True)
def staff_qualification_create(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        from .forms import StaffQualificationForm
        form = StaffQualificationForm(request.POST, staff=staff)
        if form.is_valid():
            qualification = form.save(commit=False)
            qualification.staff = staff
            qualification.save()
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        from .forms import StaffQualificationForm
        form = StaffQualificationForm(staff=staff)

    return render(request, 'staff/staff_qualification_form.html', {
        'form': form,
        'staff': staff
    })

# スタッフ資格編集
@login_required
@permission_required('staff.change_staffqualification', raise_exception=True)
def staff_qualification_update(request, pk):
    qualification = get_object_or_404(StaffQualification, pk=pk)
    staff = qualification.staff
    if request.method == 'POST':
        from .forms import StaffQualificationForm
        form = StaffQualificationForm(request.POST, instance=qualification, staff=staff)
        if form.is_valid():
            form.save()
            return redirect('staff:staff_qualification_list', staff_pk=staff.pk)
    else:
        from .forms import StaffQualificationForm
        form = StaffQualificationForm(instance=qualification, staff=staff)

    return render(request, 'staff/staff_qualification_form.html', {
        'form': form,
        'staff': staff,
        'qualification': qualification
    })

# スタッフ資格削除
@login_required
@permission_required('staff.delete_staffqualification', raise_exception=True)
def staff_qualification_delete(request, pk):
    qualification = get_object_or_404(StaffQualification, pk=pk)
    staff = qualification.staff
    if request.method == 'POST':
        qualification.delete()
        return redirect('staff:staff_qualification_list', staff_pk=staff.pk)

    return render(request, 'staff/staff_qualification_confirm_delete.html', {
        'qualification': qualification,
        'staff': staff
    })

# スタッフ技能登録
@login_required
@permission_required('staff.add_staffskill', raise_exception=True)
def staff_skill_create(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        from .forms import StaffSkillForm
        form = StaffSkillForm(request.POST, staff=staff)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.staff = staff
            skill.save()
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        from .forms import StaffSkillForm
        form = StaffSkillForm(staff=staff)

    return render(request, 'staff/staff_skill_form.html', {
        'form': form,
        'staff': staff
    })

# スタッフ技能編集
@login_required
@permission_required('staff.change_staffskill', raise_exception=True)
def staff_skill_update(request, pk):
    skill = get_object_or_404(StaffSkill, pk=pk)
    staff = skill.staff
    if request.method == 'POST':
        from .forms import StaffSkillForm
        form = StaffSkillForm(request.POST, instance=skill, staff=staff)
        if form.is_valid():
            form.save()
            return redirect('staff:staff_skill_list', staff_pk=staff.pk)
    else:
        from .forms import StaffSkillForm
        form = StaffSkillForm(instance=skill, staff=staff)

    return render(request, 'staff/staff_skill_form.html', {
        'form': form,
        'staff': staff,
        'skill': skill
    })

# スタッフ技能削除
@login_required
@permission_required('staff.delete_staffskill', raise_exception=True)
def staff_skill_delete(request, pk):
    skill = get_object_or_404(StaffSkill, pk=pk)
    staff = skill.staff
    if request.method == 'POST':
        skill.delete()
        return redirect('staff:staff_skill_list', staff_pk=staff.pk)

    return render(request, 'staff/staff_skill_confirm_delete.html', {
        'skill': skill,
        'staff': staff
    })

# スタッフ資格一覧
@login_required
@permission_required('staff.view_staffqualification', raise_exception=True)
def staff_qualification_list(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    qualifications = staff.qualifications.select_related('qualification').order_by('-acquired_date')

    return render(request, 'staff/staff_qualification_list.html', {
        'staff': staff,
        'qualifications': qualifications
    })

# スタッフ技能一覧
@login_required
@permission_required('staff.view_staffskill', raise_exception=True)
def staff_skill_list(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    skills = staff.skills.select_related('skill').order_by('-acquired_date')

    return render(request, 'staff/staff_skill_list.html', {
        'staff': staff,
        'skills': skills
    })

# ===== スタッフファイル関連ビュー =====

# スタッフファイル一覧
@login_required
@permission_required('staff.view_stafffile', raise_exception=True)
def staff_file_list(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    files = staff.files.order_by('-uploaded_at')

    paginator = Paginator(files, 20)
    page = request.GET.get('page')
    files_page = paginator.get_page(page)

    return render(request, 'staff/staff_file_list.html', {
        'staff': staff,
        'files': files_page
    })

# スタッフファイル単体アップロード
@login_required
@permission_required('staff.add_stafffile', raise_exception=True)
def staff_file_create(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        form = StaffFileForm(request.POST, request.FILES)
        if form.is_valid():
            staff_file = form.save(commit=False)
            staff_file.staff = staff
            staff_file.save()
            messages.success(request, 'ファイルをアップロードしました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffFileForm()

    return render(request, 'staff/staff_file_form.html', {
        'form': form,
        'staff': staff
    })



# スタッフファイル削除
@login_required
@permission_required('staff.delete_stafffile', raise_exception=True)
def staff_file_delete(request, pk):
    staff_file = get_object_or_404(StaffFile, pk=pk)
    staff = staff_file.staff

    if request.method == 'POST':
        # ファイルも物理削除
        if staff_file.file:
            staff_file.file.delete(save=False)
        staff_file.delete()
        messages.success(request, 'ファイルを削除しました。')
        return redirect('staff:staff_file_list', staff_pk=staff.pk)

    return render(request, 'staff/staff_file_confirm_delete.html', {
        'staff_file': staff_file,
        'staff': staff
    })

# スタッフファイルダウンロード
@login_required
@permission_required('staff.view_stafffile', raise_exception=True)
def staff_file_download(request, pk):
    staff_file = get_object_or_404(StaffFile, pk=pk)

    try:
        # ファイルの存在確認
        if not staff_file.file or not staff_file.file.name:
            messages.error(request, f'ファイル「{staff_file.original_filename}」の情報が見つかりません。')
            return redirect('staff:staff_detail', pk=staff_file.staff.pk)

        # 物理ファイルの存在確認
        import os
        if not os.path.exists(staff_file.file.path):
            messages.error(request, f'ファイル「{staff_file.original_filename}」が見つかりません。ファイルが削除されている可能性があります。')
            return redirect('staff:staff_detail', pk=staff_file.staff.pk)

        response = FileResponse(
            staff_file.file.open('rb'),
            as_attachment=True,
            filename=staff_file.original_filename
        )
        return response
    except (FileNotFoundError, OSError, ValueError) as e:
        messages.error(request, f'ファイル「{staff_file.original_filename}」のダウンロードに失敗しました。ファイルが削除されている可能性があります。')
        return redirect('staff:staff_detail', pk=staff_file.staff.pk)
    except Exception as e:
        messages.error(request, f'ファイルのダウンロード中にエラーが発生しました: {str(e)}')
        return redirect('staff:staff_detail', pk=staff_file.staff.pk)



from apps.company.models import Company, CompanyUser

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_mail_send(request, pk):
    """スタッフメール送信"""
    staff = get_object_or_404(Staff, pk=pk)

    # メールアドレスが設定されていない場合はエラー
    if not staff.email:
        messages.error(request, 'このスタッフにはメールアドレスが設定されていません。')
        return redirect('staff:staff_detail', pk=pk)

    from .forms_mail import StaffMailForm

    # ログインユーザーから会社情報を取得
    try:
        company_user = CompanyUser.objects.get(email=request.user.email)
        company = Company.objects.get(corporate_number=company_user.corporate_number)
    except (CompanyUser.DoesNotExist, Company.DoesNotExist):
        company = None
        messages.error(request, '自社情報が見つからないため、メールを送信できません。')
        return redirect('staff:staff_detail', pk=pk)

    if request.method == 'POST':
        form = StaffMailForm(staff=staff, user=request.user, company=company, data=request.POST)
        if form.is_valid():
            success, message = form.send_mail()
            if success:
                messages.success(request, message)
                return redirect('staff:staff_detail', pk=pk)
            else:
                messages.error(request, message)
    else:
        form = StaffMailForm(staff=staff, user=request.user, company=company)

    context = {
        'form': form,
        'staff': staff,
        'title': f'{staff.name_last} {staff.name_first} へのメール送信',
    }
    return render(request, 'staff/staff_mail_send.html', context)

@login_required
@permission_required('staff.change_staff', raise_exception=True)
def staff_face_upload(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        from .forms import StaffFaceUploadForm
        form = StaffFaceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data['face_image']
            x = form.cleaned_data.get('crop_x')
            y = form.cleaned_data.get('crop_y')
            w = form.cleaned_data.get('crop_width')
            h = form.cleaned_data.get('crop_height')

            # ディレクトリの存在を確認し、なければ作成
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'staff_files')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # ファイルパスを定義
            image_path = os.path.join(upload_dir, f'{staff.pk}.jpg')

            # Pillowを使って画像を切り抜き・リサイズ・保存
            try:
                with Image.open(image) as img:
                    # 元の情報の取得
                    orig_w, orig_h = img.size

                    # クロップ処理（座標が提供されている場合）
                    if all(v is not None for v in [x, y, w, h]):
                        # 念のため座標を整数に変換し、範囲内に収める
                        left = max(0, int(x))
                        top = max(0, int(y))
                        right = min(orig_w, int(x + w))
                        bottom = min(orig_h, int(y + h))
                        
                        if right > left and bottom > top:
                            img = img.crop((left, top, right, bottom))

                    # JPEGに変換可能な形式（RGB）に変換
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 600x600の正方形にリサイズ
                    img = img.resize((600, 600), Image.Resampling.LANCZOS)
                    
                    # 保存
                    img.save(image_path, 'JPEG', quality=95)
                    delete_staff_placeholder(staff.pk)
                AppLog.objects.create(
                    user=request.user,
                    model_name='Staff',
                    object_id=str(staff.pk),
                    object_repr=f'{staff} - 顔写真登録',
                    action='update'
                )
                messages.success(request, '顔写真を登録しました。')
            except Exception as e:
                messages.error(request, f'画像の保存中にエラーが発生しました: {e}')
        else:
            # フォームが無効な場合のエラーメッセージ
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

    return redirect('staff:staff_detail', pk=staff.pk)


@login_required
@permission_required('staff.change_staff', raise_exception=True)
def staff_face_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        image_path = os.path.join(settings.MEDIA_ROOT, 'staff_files', f'{staff.pk}.jpg')
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                delete_staff_placeholder(staff.pk)
                AppLog.objects.create(
                    user=request.user,
                    model_name='Staff',
                    object_id=str(staff.pk),
                    object_repr=f'{staff} - 顔写真削除',
                    action='update'
                )
                messages.success(request, '顔写真を削除しました。')
            except OSError as e:
                messages.error(request, f'ファイルの削除中にエラーが発生しました: {e}')
        else:
            messages.warning(request, '削除対象の顔写真が見つかりませんでした。')
    return redirect('staff:staff_detail', pk=staff.pk)


@login_required
def staff_favorite_add(request, staff_pk):
    """スタッフをお気に入りに追加"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    StaffFavorite.objects.get_or_create(staff=staff, user=request.user)
    messages.success(request, f'スタッフ「{staff.name}」をお気に入りに追加しました。')
    return redirect('staff:staff_detail', pk=staff_pk)


@login_required
def staff_favorite_remove(request, staff_pk):
    """スタッフをお気に入りから解除"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    StaffFavorite.objects.filter(staff=staff, user=request.user).delete()
    messages.success(request, f'スタッフ「{staff.name}」をお気に入りから解除しました。')
    return redirect('staff:staff_detail', pk=staff_pk)


@login_required
@permission_required('staff.change_staff', raise_exception=True)
def staff_tag_edit(request, pk):
    """スタッフタグの編集"""
    staff = get_object_or_404(Staff, pk=pk)
    
    if request.method == 'POST':
        form = StaffTagEditForm(request.POST, instance=staff)
        if form.is_valid():
            # 以前のタグを取得（ログ用）
            old_tag_names = ", ".join([t.name for t in staff.tags.all()])

            form.save()

            new_tag_names = ", ".join([t.name for t in staff.tags.all()])

            # AppLogに記録
            log_model_action(request.user, 'update', staff)
            AppLog.objects.create(
                user=request.user,
                action='update',
                model_name='Staff',
                object_id=str(staff.pk),
                object_repr=f"タグ変更: {old_tag_names} -> {new_tag_names}"
            )

            messages.success(request, f'スタッフ「{staff.name}」のタグを更新しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffTagEditForm(instance=staff)
    
    context = {
        'staff': staff,
        'form': form,
    }
    return render(request, 'staff/staff_tag_edit.html', context)
