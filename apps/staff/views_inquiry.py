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
from .models import Staff
from .models_inquiry import StaffInquiry, StaffInquiryMessage
from apps.company.models import CompanyUser, Company
from apps.connect.models import ConnectStaff
from .forms_inquiry import StaffInquiryForm, StaffInquiryMessageForm, StaffInquiryFromAdminForm

@login_required
def staff_inquiry_list(request):
    """問い合わせ一覧"""
    is_company_or_admin = request.user.is_superuser or CompanyUser.objects.filter(email=request.user.email).exists()
    
    # 自分の問い合わせ or 自分が担当者の問い合わせ or 管理者
    if request.user.is_superuser:
        inquiries_qs = StaffInquiry.objects.all().select_related('user')
    else:
        # CompanyUserとしての権限
        my_companies = CompanyUser.objects.filter(email=request.user.email).values_list('corporate_number', flat=True)
        # 自分が作成者 or 自分のCompanyあての問い合わせ
        inquiries_qs = StaffInquiry.objects.filter(
            models.Q(user=request.user) | models.Q(corporate_number__in=my_companies)
        ).select_related('user').distinct()
    
    # 問い合わせが1件もない場合は新規作成画面へ（一般スタッフの場合のみ）
    if not is_company_or_admin:
        if not inquiries_qs.exists():
            return redirect('staff:staff_inquiry_create')
    
    # 法人名を取得するためのマップ作成
    corporate_numbers = inquiries_qs.values_list('corporate_number', flat=True).distinct()
    companies = Company.objects.filter(corporate_number__in=corporate_numbers)
    company_name_map = {c.corporate_number: c.name for c in companies}
    
    for inquiry in inquiries_qs:
        inquiry.client_name = company_name_map.get(inquiry.corporate_number, inquiry.corporate_number)
        # 投稿者名を設定
        inquiry.user_full_name = inquiry.user.get_full_name_japanese()
    
    paginator = Paginator(inquiries_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'staff/inquiry/staff_inquiry_list.html', {
        'page_obj': page_obj,
    })

@login_required
def staff_inquiry_create(request):
    """問い合わせ新規登録"""
    is_company_or_admin = request.user.is_superuser or CompanyUser.objects.filter(email=request.user.email).exists()
    if request.method == 'POST':
        form = StaffInquiryForm(request.POST, user=request.user)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.user = request.user
            inquiry.save()
            
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
    
    if request.method == 'POST':
        # 返信時もスタッフの場合は接続承認を再確認
        if not is_company_or_admin:
            from apps.connect.models import ConnectStaff
            if not ConnectStaff.objects.filter(email=request.user.email, corporate_number=inquiry.corporate_number, status='approved').exists():
                messages.error(request, '接続承認が解除されているため、返信できません。')
                return redirect('staff:staff_inquiry_list')

        form = StaffInquiryMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.inquiry = inquiry
            message.user = request.user
            # スタッフの場合は非表示を強制的に解除
            if not is_company_or_admin:
                message.is_hidden = False
            message.save()
            
            # ログ記録
            log_model_action(request.user, 'create', message)
            
            messages.success(request, 'メッセージを投稿しました。')
            return redirect('staff:staff_inquiry_detail', pk=pk)
    else:
        form = StaffInquiryMessageForm()
    
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
        form = StaffInquiryFromAdminForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.user = staff_user
            inquiry.corporate_number = corporate_number
            inquiry.save()
            
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
