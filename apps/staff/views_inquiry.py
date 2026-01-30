from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.core.paginator import Paginator
from apps.system.logs.utils import log_model_action, log_view_detail
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required
from django.views.decorators.http import require_POST
from .models import Staff, StaffInquiry, StaffInquiryMessage
from apps.company.models import CompanyUser, Company
from apps.connect.models import ConnectStaff
from .forms_inquiry import StaffInquiryForm, StaffInquiryMessageForm, StaffInquiryFromAdminForm, StaffInquiryFilterForm
from apps.profile.decorators import check_staff_agreement

@login_required
@check_staff_agreement
@permission_required('staff.view_staffinquiry', raise_exception=True)
def staff_inquiry_list(request):
    """問い合わせ一覧"""
    is_company_or_admin = request.user.is_superuser or CompanyUser.objects.filter(email=request.user.email).exists()
    
    # 自分の問い合わせ or 自分が担当者の問い合わせ or 管理者
    if request.user.is_superuser:
        inquiries_qs = StaffInquiry.objects.all().select_related('user').order_by('-created_at')
    else:
        # CompanyUserとしての権限
        my_companies = CompanyUser.objects.filter(email=request.user.email).values_list('corporate_number', flat=True)
        # 自分が作成者 or 自分のCompanyあての問い合わせ
        inquiries_qs = StaffInquiry.objects.filter(
            models.Q(user=request.user) | models.Q(corporate_number__in=my_companies)
        ).select_related('user').distinct().order_by('-created_at')
    
    # 問い合わせが1件もない場合は新規作成画面へ（一般スタッフの場合のみ）
    if not is_company_or_admin:
        if not inquiries_qs.exists():
            return redirect('staff:staff_inquiry_create')

    # フィルタフォームの処理
    filter_form = StaffInquiryFilterForm(request.GET, is_company_or_admin=is_company_or_admin)
    if filter_form.is_valid():
        status_filter = filter_form.cleaned_data.get('status')
        if status_filter:
            if status_filter == 'unanswered' and is_company_or_admin: # company側で未回答フィルタの場合
                inquiries_qs = inquiries_qs.filter(status='open', last_message_by='staff')
            elif status_filter != 'unanswered': # その他のステータスフィルタの場合
                inquiries_qs = inquiries_qs.filter(status=status_filter)

    # 法人名を取得するためのマップ作成 (ここでinquiries_qsがフィルタされているので、最新のinquiries_qsからcorporate_numbersを取得)
    corporate_numbers = inquiries_qs.values_list('corporate_number', flat=True).distinct()
    companies = Company.objects.filter(corporate_number__in=corporate_numbers)
    company_name_map = {c.corporate_number: c.name for c in companies}
    
    staff_map = {}
    if is_company_or_admin:
        emails = inquiries_qs.values_list('user__email', flat=True).distinct()
        staffs = Staff.objects.filter(email__in=emails).select_related('regist_status', 'employment_type').prefetch_related('tags')
        staff_map = {s.email: s for s in staffs}

    processed_inquiries = []
    for inquiry in inquiries_qs:
        inquiry.client_name = company_name_map.get(inquiry.corporate_number, inquiry.corporate_number)
        # 投稿者名を設定
        inquiry.user_full_name = inquiry.user.get_full_name_japanese()

        # Staff情報を紐付け
        if is_company_or_admin:
            inquiry.staff = staff_map.get(inquiry.user.email)

        # スタッフ側の未読メッセージ判定
        is_hidden_exclude_cond = models.Q(is_hidden=False) if not is_company_or_admin else models.Q()
        inquiry.has_unread_message = inquiry.messages.filter(read_at__isnull=True).exclude(user=request.user).filter(is_hidden_exclude_cond).exists()
        
        # 会社側の未回答ステータス判定
        if is_company_or_admin and inquiry.status == 'open' and inquiry.last_message_by == 'staff':
            inquiry.is_unanswered = True
        else:
            inquiry.is_unanswered = False
        processed_inquiries.append(inquiry)

    paginator = Paginator(processed_inquiries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'staff/inquiry/staff_inquiry_list.html', {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'is_company_or_admin': is_company_or_admin, # これを追加
    })

@login_required
@check_staff_agreement
@permission_required('staff.add_staffinquiry', raise_exception=True)
def staff_inquiry_create(request):
    """問い合わせ新規登録"""
    is_company_or_admin = request.user.is_superuser or CompanyUser.objects.filter(email=request.user.email).exists()
    if request.method == 'POST':
        form = StaffInquiryForm(request.POST, user=request.user)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.user = request.user
            inquiry.inquiry_from = 'staff'
            inquiry.last_message_by = 'staff'
            inquiry.save()

            # フォームから content を取得して最初のメッセージとして保存
            content = form.cleaned_data.get('content')
            if content:
                StaffInquiryMessage.objects.create(
                    inquiry=inquiry,
                    user=request.user,
                    content=content,
                    # attachmentはフォームに含まれないので、別途処理が必要な場合は追加
                )
            
            # ログ記録
            log_model_action(request.user, 'create', inquiry)
            
            messages.success(request, '問い合わせ・ご連絡を送信しました。')
            return redirect('staff:staff_inquiry_list')
    else:
        form = StaffInquiryForm(user=request.user)
    
    return render(request, 'staff/inquiry/staff_inquiry_form.html', {
        'form': form,
        'is_company_or_admin': is_company_or_admin,
    })

@login_required
@check_staff_agreement
@permission_required('staff.view_staffinquiry', raise_exception=True)
def staff_inquiry_detail(request, pk):
    """問い合わせ詳細 & メッセージ投稿"""
    is_company_or_admin = request.user.is_superuser or CompanyUser.objects.filter(email=request.user.email).exists()
    
    # 権限確認
    if request.user.is_superuser:
        inquiry = get_object_or_404(StaffInquiry, pk=pk)
    else:
        my_companies = CompanyUser.objects.filter(email=request.user.email).values_list('corporate_number', flat=True)
        # 自分が作成者 or 自分のCompanyあての問い合わせ
        inquiry = get_object_or_404(
            StaffInquiry,
            models.Q(pk=pk) & (models.Q(user=request.user) | models.Q(corporate_number__in=my_companies))
        )
    
    # スタッフが閲覧した場合、未読の会社側メッセージを既読にする
    if not is_company_or_admin:
        inquiry.messages.exclude(user=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())

    if request.method == 'POST':
        # 完了済みの問い合わせチェック
        if inquiry.status == 'completed' and not is_company_or_admin:
             messages.error(request, 'この問い合わせは完了済みのため、メッセージを投稿できません。')
             return redirect('staff:staff_inquiry_detail', pk=pk)

        # 返信時もスタッフの場合は接続承認を再確認
        if not is_company_or_admin:
            from apps.connect.models import ConnectStaff
            if not ConnectStaff.objects.filter(email=request.user.email, corporate_number=inquiry.corporate_number, status='approved').exists():
                messages.error(request, '接続承認が解除されているため、返信できません。')
                return redirect('staff:staff_inquiry_list')

        form = StaffInquiryMessageForm(request.POST, request.FILES, is_company=is_company_or_admin)
        if form.is_valid():
            message = form.save(commit=False)
            message.inquiry = inquiry
            message.user = request.user
            
            # スタッフの場合は非表示を強制的に解除
            if not is_company_or_admin:
                message.is_hidden = False
            message.save()
            
            # 問い合わせの最終投稿者を更新
            # sender_type removed, determine by user role
            sender_type_val = 'company' if is_company_or_admin else 'staff'
            inquiry.last_message_by = sender_type_val
            inquiry.save()
            
            # ログ記録
            log_model_action(request.user, 'create', message)
            
            messages.success(request, 'メッセージを投稿しました。')
            return redirect('staff:staff_inquiry_detail', pk=pk)
    else:
        form = StaffInquiryMessageForm(is_company=is_company_or_admin)
    
    # 法人名を取得
    company = Company.objects.filter(corporate_number=inquiry.corporate_number).first()
    inquiry.client_name = company.name if company else inquiry.corporate_number
    
    # メッセージ一覧
    messages_qs = inquiry.messages.all().order_by('created_at')
    
    # スタッフ（作成者）の場合は非表示メッセージを除外
    if not is_company_or_admin:
        messages_qs = messages_qs.filter(is_hidden=False)
    
    now = timezone.now()
    for m in messages_qs:
        # 5分以内 & 自分の投稿であれば削除可能
        m.can_delete = (m.user == request.user and now - m.created_at < timedelta(minutes=5))
    
    # ログ記録
    log_view_detail(request.user, inquiry)
    
    return render(request, 'staff/inquiry/staff_inquiry_detail.html', {
        'inquiry': inquiry,
        'messages_qs': messages_qs,
        'form': form,
        'is_company_or_admin': is_company_or_admin,
    })

@login_required
@check_staff_agreement
@permission_required('staff.delete_staffinquirymessage', raise_exception=True)
def staff_inquiry_message_delete(request, pk):
    """メッセージ削除 (5分以内)"""
    message_obj = get_object_or_404(StaffInquiryMessage, pk=pk)
    
    # 権限チェック: 自分の投稿 & 5分以内
    now = timezone.now()
    if message_obj.user != request.user:
        messages.error(request, '他人のメッセージは削除できません。')
    elif now - message_obj.created_at >= timedelta(minutes=5):
        messages.error(request, '投稿から5分以上経過したメッセージは削除できません。')
    else:
        inquiry_pk = message_obj.inquiry.pk
        # ログ記録
        log_model_action(request.user, 'delete', message_obj)
        message_obj.delete()
        messages.success(request, 'メッセージを削除しました。')
        return redirect('staff:staff_inquiry_detail', pk=inquiry_pk)
    
    return redirect('staff:staff_inquiry_detail', pk=message_obj.inquiry.pk)

@login_required
@permission_required('staff.view_staff', raise_exception=True)
@permission_required('staff.add_staffinquiry', raise_exception=True)
@check_staff_agreement
def staff_inquiry_create_for_staff(request, staff_pk):
    """会社からスタッフへのメッセージ連絡"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    User = get_user_model()
    
    # 会社の法人番号を取得（最初の会社を仮定）
    company = Company.objects.first()
    corporate_number = company.corporate_number if company else None
    
    if not staff.email:
        messages.error(request, 'このスタッフにはメールアドレスが設定されていません。')
        return redirect('staff:staff_detail', pk=staff_pk)

    # 接続・承認状況の確認
    if not corporate_number:
        messages.error(request, '会社情報が設定されていません。')
        return redirect('staff:staff_detail', pk=staff_pk)
        
    connect_request = ConnectStaff.objects.filter(
        email=staff.email, 
        corporate_number=corporate_number, 
        status='approved'
    ).first()
    
    if not connect_request:
        messages.error(request, 'このスタッフは接続承認されていません。')
        return redirect('staff:staff_detail', pk=staff_pk)

    # スタッフのユーザーアカウント確認
    staff_user = User.objects.filter(email=staff.email).first()
    if not staff_user:
        messages.error(request, 'このスタッフのユーザーアカウントが見つかりません。')
        return redirect('staff:staff_detail', pk=staff_pk)

    if request.method == 'POST':
        form = StaffInquiryFromAdminForm(request.POST, request.FILES)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.user = staff_user
            inquiry.corporate_number = corporate_number
            inquiry.inquiry_from = 'company'
            inquiry.last_message_by = 'company'
            inquiry.attachment = None  # StaffInquiry自体のattachmentは使わない
            inquiry.save()
            
            # フォームから content と attachment を取得して最初のメッセージとして保存
            content = form.cleaned_data.get('content')
            attachment = form.cleaned_data.get('attachment')
            if content or attachment:
                StaffInquiryMessage.objects.create(
                    inquiry=inquiry,
                    user=request.user,  # 投稿者は管理者
                    content=content,
                    attachment=attachment,
                    is_hidden=False # 必要に応じて
                )
            
            # ログ記録
            log_model_action(request.user, 'create', inquiry)
            
            messages.success(request, 'メッセージを送信しました。')
            return redirect('staff:staff_inquiry_detail', pk=inquiry.pk)
    else:
        form = StaffInquiryFromAdminForm()

    return render(request, 'staff/inquiry/staff_inquiry_from_company.html', {
        'form': form,
        'staff': staff,
        'title': f'{staff.name_last} {staff.name_first} へのメッセージ連絡',
    })

@login_required
@require_POST
@permission_required('staff.change_staffinquiry', raise_exception=True)
def staff_inquiry_toggle_status(request, pk):
    """問い合わせのステータスを切り替える"""
    # 権限確認
    if request.user.is_superuser:
        inquiry = get_object_or_404(StaffInquiry, pk=pk)
    else:
        my_companies = CompanyUser.objects.filter(email=request.user.email).values_list('corporate_number', flat=True)
        inquiry = get_object_or_404(
            StaffInquiry,
            models.Q(pk=pk) & (models.Q(user=request.user) | models.Q(corporate_number__in=my_companies))
        )

    # ステータスを切り替え
    # ステータスを切り替え
    if inquiry.status == 'open':
        inquiry.status = 'completed'
        messages.success(request, 'この問い合わせを「完了」にしました。')
    else:
        # already completed, do not allow reopen based on requirements
        # "問い合わせは、スタッフもcompany側も「受付中に戻す」ボタン・昨日は無しとする"
        messages.error(request, '完了済みの問い合わせを再開することはできません。')
        return redirect('staff:staff_inquiry_detail', pk=pk)
    inquiry.save()

    # ログ記録
    log_model_action(request.user, 'change', inquiry)

    return redirect('staff:staff_inquiry_detail', pk=pk)
