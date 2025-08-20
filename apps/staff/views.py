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

from .models import Staff, StaffContacted, StaffQualification, StaffSkill, StaffFile, StaffMyNumberRecord
from .forms import StaffForm, StaffContactedForm, StaffFileForm, StaffMyNumberRecordForm
from apps.system.settings.utils import my_parameter
from apps.system.settings.models import Dropdowns
from apps.system.logs.models import AppLog
from apps.common.utils import fill_excel_from_template, fill_pdf_from_template

# ロガーの作成
logger = logging.getLogger('staff')

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_change_history_list(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    # スタッフ、資格、技能、ファイルの変更履歴を含む
    from django.db import models as django_models
    logs = AppLog.objects.filter(
        django_models.Q(model_name='Staff', object_id=str(staff.pk)) |
        django_models.Q(model_name='StaffQualification', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='StaffSkill', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='StaffFile', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='ConnectStaff', object_id=str(staff.pk)),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    return render(request, 'staff/staff_change_history_list.html', {'staff': staff, 'logs': logs_page})

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
    sort = request.GET.get('sort', 'pk')  # デフォルトソートをpkに設定
    query = request.GET.get('q', '').strip()
    regist_form_filter = request.GET.get('regist_form', '').strip()  # 登録区分フィルター
    department_filter = request.GET.get('department', '').strip()  # 所属部署フィルター
    
    # 基本のクエリセット
    staffs = Staff.objects.all()

    # 会社の法人番号を取得（最初の会社を仮定）
    from apps.company.models import Company
    company = Company.objects.first()
    corporate_number = company.corporate_number if company else None
    
    # キーワード検索
    if query:
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
    if regist_form_filter:
        staffs = staffs.filter(regist_form_code=regist_form_filter)
    
    # 所属部署での絞り込み
    if department_filter:
        staffs = staffs.filter(department_code=department_filter)

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
    regist_form_options = Dropdowns.objects.filter(
        category='regist_form', 
        active=True
    ).order_by('disp_seq')
    
    # 各オプションに選択状態を追加
    for option in regist_form_options:
        option.is_selected = (regist_form_filter == option.value)
    
    # 所属部署の選択肢を取得（現在有効な部署のみ）
    from apps.company.models import CompanyDepartment
    from django.utils import timezone
    current_date = timezone.now().date()
    department_options = CompanyDepartment.get_valid_departments(current_date)
    
    # 各部署オプションに選択状態を追加
    for dept in department_options:
        dept.is_selected = (department_filter == dept.department_code)

    paginator = Paginator(staffs, 10)  # 1ページあたり10件表示
    page_number = request.GET.get('page')  # URLからページ番号を取得
    staffs_pages = paginator.get_page(page_number)

    # 各スタッフが接続承認済みかどうかを判定し、オブジェクトに属性を付与
    from apps.connect.models import ConnectStaff
    if corporate_number:
        for staff in staffs_pages:
            if staff.email:
                staff.is_connected_approved = ConnectStaff.objects.filter(
                    corporate_number=corporate_number,
                    email=staff.email,
                    status='approved'
                ).exists()
            else:
                staff.is_connected_approved = False
    else:
        for staff in staffs_pages:
            staff.is_connected_approved = False

    return render(request, 'staff/staff_list.html', {
        'staffs': staffs_pages, 
        'query': query, 
        'sort': sort,
        'regist_form_filter': regist_form_filter,
        'regist_form_options': regist_form_options,
        'department_filter': department_filter,
        'department_options': department_options,
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
                        messages.success(request, f'{staff}への接続依頼を取り消しました。')
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
                        messages.success(request, f'{staff}に接続依頼を送信しました。')
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
    # 連絡履歴（最新5件）
    contacted_list = staff.contacted_histories.all()[:5]
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
    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    log_view_detail(request.user, staff)
    # 変更履歴（AppLogから取得、最新5件）- スタッフ、資格、技能、ファイルの変更を含む
    from django.db import models as django_models
    change_logs = AppLog.objects.filter(
        django_models.Q(model_name='Staff', object_id=str(staff.pk)) |
        django_models.Q(model_name='StaffQualification', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='StaffSkill', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='StaffFile', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='ConnectStaff', object_id=str(staff.pk)),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]
    change_logs_count = AppLog.objects.filter(
        django_models.Q(model_name='Staff', object_id=str(staff.pk)) |
        django_models.Q(model_name='StaffQualification', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='StaffSkill', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='StaffFile', object_repr__startswith=f'{staff} - ') |
        django_models.Q(model_name='ConnectStaff', object_id=str(staff.pk)),
        action__in=['create', 'update', 'delete']
    ).count()
    
    # 接続関連情報を取得
    connect_request = None
    if staff.email:
        from apps.connect.models import ConnectStaff
        from apps.company.models import Company
        try:
            # 現在のユーザーの会社の法人番号を取得
            company = Company.objects.first()  # 仮の実装、実際は適切な会社を取得
            if company and company.corporate_number:
                connect_request = ConnectStaff.objects.filter(
                    corporate_number=company.corporate_number,
                    email=staff.email
                ).first()
        except Exception:
            pass
    
    return render(request, 'staff/staff_detail.html', {
        'staff': staff,
        'contacted_list': contacted_list,
        'staff_contracts': staff_contracts,
        'staff_contracts_count': staff_contracts_count,
        'qualifications': qualifications,
        'skills': skills,
        'files': files,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
        'connect_request': connect_request,
    })

# 連絡履歴 登録
@login_required
@permission_required('staff.add_staffcontacted', raise_exception=True)
def staff_contacted_create(request, staff_pk):
    from django.utils import timezone
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
            log_model_action(request.user, 'update', contacted)
            messages.success(request, '連絡履歴を更新しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffContactedForm(instance=contacted)
    return render(request, 'staff/staff_contacted_form.html', {'form': form, 'staff': staff, 'contacted': contacted})

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
                log_model_action(request.user, 'update', staff)
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
    image_path = os.path.join(my_parameter("STAFF_FACE_PATH"), str(staff.pk)+".jpg") 
    logger.error(image_path)

    # 画像ファイルが存在する場合はそのファイルを返す
    if image_path and os.path.exists(image_path):
        return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')
    
    # 画像が存在しない場合、名前を使って画像を生成
    response = HttpResponse(content_type="image/jpeg")
    image = Image.new("RGB", (200, 200), (200, 200, 200))  # 背景色の指定
    if staff.sex == 1:
        image = Image.new("RGB", (200, 200), (140, 140, 240))  # 背景色の指定
    elif staff.sex == 2:
        image = Image.new("RGB", (200, 200), (240, 140, 140))  # 背景色の指定
    
    
    draw = ImageDraw.Draw(image)
    
    # 日本語フォントの設定
    font_path = os.path.join(settings.BASE_DIR, 'statics/fonts/ipagp.ttf')
    try:
        font = ImageFont.truetype(font_path,80)#font-size
    except IOError:
        logger.error(font_path)
    
    # 名前を中央に描画
    # 名・姓が両方とも存在する場合のみイニシャルを生成
    if staff.name_last and staff.name_first:
        initials = f"{staff.name_last[0]}{staff.name_first[0]}"
    else:
        initials = ""  # 片方がない場合は空欄を返すなど
    # `textbbox` を使ってテキストのバウンディングボックスを取得
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((200 - text_width) // 2, (200 - text_height-20) // 2)
    draw.text(position, initials, fill="white", font=font)
    
    # 画像をHTTPレスポンスとして返す
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

@login_required
@permission_required('staff.view_staff', raise_exception=True)
def staff_fuyokojo(request, pk):
    staff = Staff.objects.get(pk=pk)
    sex_dropdown = Dropdowns.objects.filter(category='sex', value=staff.sex, active=True).first()

    # フォームに埋め込むデータを準備
    form_data = {
        'Text6': staff.name_kana_last + " " + staff.name_kana_first,  # カナ名
        'Text7': staff.name_last + " " + staff.name_first,  # 名前
        'Text10': staff.address1 + staff.address2 + staff.address3,  # 住所
    }

    # PDFフォームにデータを埋め込む（メモリ上にPDFを作成）
    output_pdf = fill_pdf_from_template('templates/pdfs/2025bun_01_input.pdf', form_data)

    # メモリ上のPDFをレスポンスとして返す
    response = HttpResponse(output_pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="staff_fuyokojo_'+str(pk)+'.pdf"'
    return response

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
    
    if request.method == 'POST':
        form = StaffMailForm(staff=staff, user=request.user, data=request.POST)
        if form.is_valid():
            success, message = form.send_mail()
            if success:
                messages.success(request, message)
                return redirect('staff:staff_detail', pk=pk)
            else:
                messages.error(request, message)
    else:
        form = StaffMailForm(staff=staff, user=request.user)
    
    context = {
        'form': form,
        'staff': staff,
        'title': f'{staff.name_last} {staff.name_first} へのメール送信',
    }
    return render(request, 'staff/staff_mail_send.html', context)


# ===== スタッフマイナンバー関連ビュー =====

@login_required
@permission_required('staff.view_staffmynumberrecord', raise_exception=True)
def staff_mynumber_detail(request, staff_id):
    """スタッフのマイナンバー詳細表示"""
    staff = get_object_or_404(Staff, pk=staff_id)
    try:
        mynumber = StaffMyNumberRecord.objects.get(staff=staff)
    except StaffMyNumberRecord.DoesNotExist:
        # 未登録の場合は登録画面へリダイレクト
        return redirect('staff:staff_mynumber_create', staff_id=staff.pk)

    context = {
        'staff': staff,
        'mynumber': mynumber,
    }
    return render(request, 'staff/staff_mynumber_detail.html', context)


@login_required
@permission_required('staff.add_staffmynumberrecord', raise_exception=True)
def staff_mynumber_create(request, staff_id):
    """スタッフのマイナンバー登録"""
    staff = get_object_or_404(Staff, pk=staff_id)
    # 既に登録済みの場合は編集画面へリダイレクト
    if hasattr(staff, 'mynumber'):
        return redirect('staff:staff_mynumber_edit', staff_id=staff.pk)

    if request.method == 'POST':
        form = StaffMyNumberRecordForm(request.POST)
        if form.is_valid():
            mynumber = form.save(commit=False)
            mynumber.staff = staff
            mynumber.save()
            messages.success(request, 'マイナンバーを登録しました。')
            return redirect('staff:staff_mynumber_detail', staff_id=staff.pk)
    else:
        form = StaffMyNumberRecordForm()

    context = {
        'form': form,
        'staff': staff,
        'is_new': True,
    }
    return render(request, 'staff/staff_mynumber_form.html', context)


@login_required
@permission_required('staff.change_staffmynumberrecord', raise_exception=True)
def staff_mynumber_edit(request, staff_id):
    """スタッフのマイナンバー編集"""
    staff = get_object_or_404(Staff, pk=staff_id)
    mynumber = get_object_or_404(StaffMyNumberRecord, staff=staff)

    if request.method == 'POST':
        form = StaffMyNumberRecordForm(request.POST, instance=mynumber)
        if form.is_valid():
            form.save()
            messages.success(request, 'マイナンバーを更新しました。')
            return redirect('staff:staff_mynumber_detail', staff_id=staff.pk)
    else:
        form = StaffMyNumberRecordForm(instance=mynumber)

    context = {
        'form': form,
        'staff': staff,
        'mynumber': mynumber,
        'is_new': False,
    }
    return render(request, 'staff/staff_mynumber_form.html', context)


@login_required
@permission_required('staff.delete_staffmynumberrecord', raise_exception=True)
def staff_mynumber_delete(request, staff_id):
    """スタッフのマイナンバー削除確認"""
    staff = get_object_or_404(Staff, pk=staff_id)
    mynumber = get_object_or_404(StaffMyNumberRecord, staff=staff)

    if request.method == 'POST':
        mynumber.delete()
        messages.success(request, 'マイナンバーを削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'mynumber': mynumber,
    }
    return render(request, 'staff/staff_mynumber_confirm_delete.html', context)