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

from .models import Staff, StaffContacted, StaffQualification, StaffSkill, StaffFile, StaffMynumber, StaffBank, StaffInternational, StaffDisability, StaffContact
from .forms import StaffMynumberForm, StaffBankForm, StaffInternationalForm, StaffDisabilityForm, StaffContactForm
from apps.system.settings.utils import my_parameter
from apps.system.settings.models import Dropdowns
from apps.system.logs.models import AppLog
from apps.common.utils import fill_excel_from_template  # , fill_pdf_from_template
from apps.common.constants import Constants
from django.http import HttpResponse
from .resources import StaffResource
import datetime

# ロガーの作成
logger = logging.getLogger('staff')


@login_required
@permission_required('staff.change_staff', raise_exception=True)
def staff_profile_request_detail(request, staff_pk, pk):
    """プロフィール申請の詳細、承認・却下"""
    from apps.connect.models import ProfileRequest
    staff = get_object_or_404(Staff, pk=staff_pk)
    profile_request = get_object_or_404(ProfileRequest, pk=pk, connect_staff__email=staff.email)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            # 承認処理
            success, message = profile_request.approve(request.user)
            if success:
                log_model_action(request.user, 'update', profile_request)
                messages.success(request, message)
            else:
                messages.error(request, message)

        elif action == 'reject':
            # 却下処理
            success, message = profile_request.reject(request.user)
            if success:
                log_model_action(request.user, 'update', profile_request)
                messages.warning(request, message)
            else:
                messages.error(request, message)

        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'profile_request': profile_request,
    }
    return render(request, 'staff/staff_profile_request_detail.html', context)


# ===== スタッフマイナンバー関連ビュー =====

@login_required
@permission_required('staff.view_staffmynumber', raise_exception=True)
def staff_mynumber_detail(request, staff_id):
    """スタッフのマイナンバー詳細表示"""
    staff = get_object_or_404(Staff, pk=staff_id)
    try:
        mynumber = StaffMynumber.objects.get(staff=staff)
    except StaffMynumber.DoesNotExist:
        # 未登録の場合は登録画面へリダイレクト
        return redirect('staff:staff_mynumber_create', staff_id=staff.pk)

    context = {
        'staff': staff,
        'mynumber': mynumber,
    }
    return render(request, 'staff/staff_mynumber_detail.html', context)


@login_required
@permission_required('staff.add_staffmynumber', raise_exception=True)
def staff_mynumber_create(request, staff_id):
    """スタッフのマイナンバー登録"""
    staff = get_object_or_404(Staff, pk=staff_id)
    # 既に登録済みの場合は編集画面へリダイレクト
    if hasattr(staff, 'mynumber'):
        return redirect('staff:staff_mynumber_edit', staff_id=staff.pk)

    if request.method == 'POST':
        form = StaffMynumberForm(request.POST)
        if form.is_valid():
            mynumber = form.save(commit=False)
            mynumber.staff = staff
            mynumber.save()
            messages.success(request, 'マイナンバーを登録しました。')
            return redirect('staff:staff_mynumber_detail', staff_id=staff.pk)
    else:
        form = StaffMynumberForm()

    context = {
        'form': form,
        'staff': staff,
        'is_new': True,
    }
    return render(request, 'staff/staff_mynumber_form.html', context)


@login_required
@permission_required('staff.change_staffmynumber', raise_exception=True)
def staff_mynumber_edit(request, staff_id):
    """スタッフのマイナンバー編集"""
    staff = get_object_or_404(Staff, pk=staff_id)
    mynumber = get_object_or_404(StaffMynumber, staff=staff)

    if request.method == 'POST':
        form = StaffMynumberForm(request.POST, instance=mynumber)
        if form.is_valid():
            form.save()
            messages.success(request, 'マイナンバーを更新しました。')
            return redirect('staff:staff_mynumber_detail', staff_id=staff.pk)
    else:
        form = StaffMynumberForm(instance=mynumber)

    context = {
        'form': form,
        'staff': staff,
        'mynumber': mynumber,
        'is_new': False,
    }
    return render(request, 'staff/staff_mynumber_form.html', context)


@login_required
@permission_required('staff.delete_staffmynumber', raise_exception=True)
def staff_mynumber_delete(request, staff_id):
    """スタッフのマイナンバー削除確認"""
    staff = get_object_or_404(Staff, pk=staff_id)
    mynumber = get_object_or_404(StaffMynumber, staff=staff)

    if request.method == 'POST':
        mynumber.delete()
        messages.success(request, 'マイナンバーを削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'mynumber': mynumber,
    }
    return render(request, 'staff/staff_mynumber_confirm_delete.html', context)


# ===== スタッフ連絡先情報関連ビュー =====

@login_required
@permission_required('staff.view_staffcontact', raise_exception=True)
def staff_contact_detail(request, staff_id):
    """スタッフの連絡先情報詳細表示"""
    staff = get_object_or_404(Staff, pk=staff_id)
    try:
        contact = StaffContact.objects.get(staff=staff)
    except StaffContact.DoesNotExist:
        # 未登録の場合は登録画面へリダイレクト
        return redirect('staff:staff_contact_create', staff_id=staff.pk)

    context = {
        'staff': staff,
        'contact': contact,
    }
    return render(request, 'staff/staff_contact_detail.html', context)


@login_required
@permission_required('staff.add_staffcontact', raise_exception=True)
def staff_contact_create(request, staff_id):
    """スタッフの連絡先情報登録"""
    staff = get_object_or_404(Staff, pk=staff_id)
    # 既に登録済みの場合は編集画面へリダイレクト
    if hasattr(staff, 'contact'):
        return redirect('staff:staff_contact_edit', staff_id=staff.pk)

    if request.method == 'POST':
        form = StaffContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.staff = staff
            contact.save()
            messages.success(request, '連絡先情報を登録しました。')
            return redirect('staff:staff_contact_detail', staff_id=staff.pk)
    else:
        form = StaffContactForm()

    context = {
        'form': form,
        'staff': staff,
        'is_new': True,
    }
    return render(request, 'staff/staff_contact_form.html', context)


@login_required
@permission_required('staff.change_staffcontact', raise_exception=True)
def staff_contact_edit(request, staff_id):
    """スタッフの連絡先情報編集"""
    staff = get_object_or_404(Staff, pk=staff_id)
    contact = get_object_or_404(StaffContact, staff=staff)

    if request.method == 'POST':
        form = StaffContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, '連絡先情報を更新しました。')
            return redirect('staff:staff_contact_detail', staff_id=staff.pk)
    else:
        form = StaffContactForm(instance=contact)

    context = {
        'form': form,
        'staff': staff,
        'contact': contact,
        'is_new': False,
    }
    return render(request, 'staff/staff_contact_form.html', context)


@login_required
@permission_required('staff.delete_staffcontact', raise_exception=True)
def staff_contact_delete(request, staff_id):
    """スタッフの連絡先情報削除確認"""
    staff = get_object_or_404(Staff, pk=staff_id)
    contact = get_object_or_404(StaffContact, staff=staff)

    if request.method == 'POST':
        contact.delete()
        messages.success(request, '連絡先情報を削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'contact': contact,
    }
    return render(request, 'staff/staff_contact_confirm_delete.html', context)


# ===== スタッフ障害者情報関連ビュー =====

@login_required
@permission_required('staff.view_staffdisability', raise_exception=True)
def staff_disability_detail(request, staff_pk):
    """スタッフの障害者情報詳細表示"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    try:
        disability = StaffDisability.objects.get(staff=staff)
    except StaffDisability.DoesNotExist:
        # 未登録の場合は登録画面へリダイレクト
        return redirect('staff:staff_disability_create', staff_pk=staff.pk)

    context = {
        'staff': staff,
        'disability': disability,
    }
    return render(request, 'staff/staff_disability_detail.html', context)


@login_required
@permission_required('staff.add_staffdisability', raise_exception=True)
def staff_disability_create(request, staff_pk):
    """スタッフの障害者情報登録"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    # 既に登録済みの場合は編集画面へリダイレクト
    if hasattr(staff, 'disability'):
        return redirect('staff:staff_disability_edit', staff_pk=staff.pk)

    if request.method == 'POST':
        form = StaffDisabilityForm(request.POST)
        if form.is_valid():
            disability = form.save(commit=False)
            disability.staff = staff
            disability.save()
            messages.success(request, '障害者情報を登録しました。')
            return redirect('staff:staff_disability_detail', staff_pk=staff.pk)
    else:
        form = StaffDisabilityForm()

    context = {
        'form': form,
        'staff': staff,
        'is_new': True,
    }
    return render(request, 'staff/staff_disability_form.html', context)


@login_required
@permission_required('staff.change_staffdisability', raise_exception=True)
def staff_disability_edit(request, staff_pk):
    """スタッフの障害者情報編集"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    disability = get_object_or_404(StaffDisability, staff=staff)

    if request.method == 'POST':
        form = StaffDisabilityForm(request.POST, instance=disability)
        if form.is_valid():
            form.save()
            messages.success(request, '障害者情報を更新しました。')
            return redirect('staff:staff_disability_detail', staff_pk=staff.pk)
    else:
        form = StaffDisabilityForm(instance=disability)

    context = {
        'form': form,
        'staff': staff,
        'disability': disability,
        'is_new': False,
    }
    return render(request, 'staff/staff_disability_form.html', context)


@login_required
@permission_required('staff.delete_staffdisability', raise_exception=True)
def staff_disability_delete(request, staff_pk):
    """スタッフの障害者情報削除確認"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    disability = get_object_or_404(StaffDisability, staff=staff)

    if request.method == 'POST':
        disability.delete()
        messages.success(request, '障害者情報を削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'disability': disability,
    }
    return render(request, 'staff/staff_disability_confirm_delete.html', context)


@login_required
@permission_required('staff.change_staffdisability', raise_exception=True)
def staff_disability_request_detail(request, staff_pk, pk):
    """障害者情報申請の詳細、承認・却下"""
    from apps.connect.models import DisabilityRequest
    staff = get_object_or_404(Staff, pk=staff_pk)
    disability_request = get_object_or_404(DisabilityRequest, pk=pk, connect_staff__email=staff.email)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            # 承認処理
            try:
                # 申請から情報を取得
                profile_disability = disability_request.profile_disability

                # スタッフの障害者情報を更新または作成
                staff_disability, created = StaffDisability.objects.update_or_create(
                    staff=staff,
                    defaults={
                        'disability_type': profile_disability.disability_type,
                        'disability_grade': profile_disability.disability_grade,
                    }
                )

                # 申請ステータスを更新
                disability_request.status = 'approved'
                disability_request.save()

                messages.success(request, f'障害者情報申請を承認し、{staff.name}の情報を更新しました。')
            except Exception as e:
                messages.error(request, f'承認処理中にエラーが発生しました: {e}')

        elif action == 'reject':
            # 却下処理
            disability_request.status = 'rejected'
            disability_request.save()
            log_model_action(request.user, 'update', disability_request)
            messages.warning(request, '障害者情報申請を却下しました。')

        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'disability_request': disability_request,
    }
    return render(request, 'staff/staff_disability_request_detail.html', context)


@login_required
@permission_required('staff.change_staffcontact', raise_exception=True)
def staff_contact_request_detail(request, staff_pk, pk):
    """連絡先情報申請の詳細、承認・却下"""
    from apps.connect.models import ContactRequest
    staff = get_object_or_404(Staff, pk=staff_pk)
    contact_request = get_object_or_404(ContactRequest, pk=pk, connect_staff__email=staff.email)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            # 承認処理
            try:
                # 申請から情報を取得
                profile_contact = contact_request.staff_profile_contact

                # スタッフの連絡先情報を更新または作成
                staff_contact, created = StaffContact.objects.update_or_create(
                    staff=staff,
                    defaults={
                        'emergency_contact': profile_contact.emergency_contact,
                        'relationship': profile_contact.relationship,
                        'postal_code': profile_contact.postal_code,
                        'address1': profile_contact.address1,
                        'address2': profile_contact.address2,
                        'address3': profile_contact.address3,
                    }
                )

                # 申請ステータスを更新
                contact_request.status = 'approved'
                contact_request.save()

                messages.success(request, f'連絡先情報申請を承認し、{staff.name}の情報を更新しました。')
            except Exception as e:
                messages.error(request, f'承認処理中にエラーが発生しました: {e}')

        elif action == 'reject':
            # 却下処理
            contact_request.status = 'rejected'
            contact_request.save()
            log_model_action(request.user, 'update', contact_request)
            messages.warning(request, '連絡先情報申請を却下しました。')

        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'contact_request': contact_request,
    }
    return render(request, 'staff/staff_contact_request_detail.html', context)


@login_required
@permission_required('staff.change_staffmynumber', raise_exception=True)
def staff_mynumber_request_detail(request, staff_pk, pk):
    """マイナンバー申請の詳細、承認・却下"""
    from apps.connect.models import MynumberRequest
    staff = get_object_or_404(Staff, pk=staff_pk)
    mynumber_request = get_object_or_404(MynumberRequest, pk=pk, connect_staff__email=staff.email)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            # 承認処理
            try:
                # 申請からマイナンバー情報を取得
                profile_mynumber = mynumber_request.profile_mynumber

                # スタッフのマイナンバーを更新または作成
                staff_mynumber, created = StaffMynumber.objects.update_or_create(
                    staff=staff,
                    defaults={'mynumber': profile_mynumber.mynumber}
                )

                # 申請ステータスを更新
                mynumber_request.status = 'approved'
                mynumber_request.save()

                messages.success(request, f'マイナンバー申請を承認し、{staff.name}のマイナンバーを更新しました。')
            except Exception as e:
                messages.error(request, f'承認処理中にエラーが発生しました: {e}')

        elif action == 'reject':
            # 却下処理
            mynumber_request.status = 'rejected'
            mynumber_request.save()
            log_model_action(request.user, 'update', mynumber_request)
            messages.warning(request, 'マイナンバー申請を却下しました。')

        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'mynumber_request': mynumber_request,
    }
    return render(request, 'staff/staff_mynumber_request_detail.html', context)


@login_required
@permission_required('staff.view_staffbank', raise_exception=True)
def staff_bank_detail(request, staff_id):
    """スタッフの銀行情報詳細表示"""
    staff = get_object_or_404(Staff, pk=staff_id)
    try:
        bank = staff.bank
    except StaffBank.DoesNotExist:
        # 未登録の場合は登録画面へリダイレクト
        return redirect('staff:staff_bank_create', staff_id=staff.pk)

    context = {
        'staff': staff,
        'bank': bank,
    }
    return render(request, 'staff/staff_bank_detail.html', context)


@login_required
@permission_required('staff.add_staffbank', raise_exception=True)
def staff_bank_create(request, staff_id):
    """スタッフの銀行情報登録"""
    staff = get_object_or_404(Staff, pk=staff_id)
    # 既に登録済みの場合は編集画面へリダイレクト
    if hasattr(staff, 'bank'):
        return redirect('staff:staff_bank_edit', staff_id=staff.pk)

    if request.method == 'POST':
        form = StaffBankForm(request.POST)
        if form.is_valid():
            bank = form.save(commit=False)
            bank.staff = staff
            bank.save()
            messages.success(request, '銀行情報を登録しました。')
            return redirect('staff:staff_bank_detail', staff_id=staff.pk)
    else:
        initial_data = {
            'account_holder': f'{staff.name_kana_last} {staff.name_kana_first}'.strip()
        }
        form = StaffBankForm(initial=initial_data)

    context = {
        'staff': staff,
        'form': form,
        'is_new': True,
    }
    return render(request, 'staff/staff_bank_form.html', context)


@login_required
@permission_required('staff.change_staffbank', raise_exception=True)
def staff_bank_edit(request, staff_id):
    """スタッフの銀行情報編集"""
    staff = get_object_or_404(Staff, pk=staff_id)
    bank = get_object_or_404(StaffBank, staff=staff)

    if request.method == 'POST':
        form = StaffBankForm(request.POST, instance=bank)
        if form.is_valid():
            form.save()
            messages.success(request, '銀行情報を更新しました。')
            return redirect('staff:staff_bank_detail', staff_id=staff.pk)
    else:
        initial_data = {
            'bank_name': bank.bank_name,
            'branch_name': bank.branch_name,
        }
        form = StaffBankForm(instance=bank, initial=initial_data)

    context = {
        'staff': staff,
        'form': form,
        'bank': bank,
        'is_new': False,
    }
    return render(request, 'staff/staff_bank_form.html', context)


@login_required
@permission_required('staff.delete_staffbank', raise_exception=True)
def staff_bank_delete(request, staff_id):
    """スタッフの銀行情報削除確認"""
    staff = get_object_or_404(Staff, pk=staff_id)
    bank = get_object_or_404(StaffBank, staff=staff)

    if request.method == 'POST':
        bank.delete()
        messages.success(request, '銀行情報を削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'bank': bank,
    }
    return render(request, 'staff/staff_bank_confirm_delete.html', context)


@login_required
@permission_required('staff.change_staffbank', raise_exception=True)
def staff_bank_request_detail(request, staff_pk, pk):
    """銀行情報申請の詳細、承認・却下"""
    from apps.connect.models import BankRequest
    staff = get_object_or_404(Staff, pk=staff_pk)
    bank_request = get_object_or_404(BankRequest, pk=pk, connect_staff__email=staff.email)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            # 承認処理
            try:
                # 申請から銀行情報を取得
                bank_profile = bank_request.staff_bank_profile

                # スタッフの銀行情報を更新または作成
                staff_bank, created = StaffBank.objects.update_or_create(
                    staff=staff,
                    defaults={
                        'bank_code': bank_profile.bank_code,
                        'branch_code': bank_profile.branch_code,
                        'account_type': bank_profile.account_type,
                        'account_number': bank_profile.account_number,
                        'account_holder': bank_profile.account_holder,
                    }
                )

                # 申請ステータスを更新
                bank_request.status = 'approved'
                bank_request.save()

                messages.success(request, f'銀行情報申請を承認し、{staff.name}の銀行情報を更新しました。')
            except Exception as e:
                messages.error(request, f'承認処理中にエラーが発生しました: {e}')

        elif action == 'reject':
            # 却下処理
            bank_request.status = 'rejected'
            bank_request.save()
            log_model_action(request.user, 'update', bank_request)
            messages.warning(request, '銀行情報申請を却下しました。')

        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'bank_request': bank_request,
    }
    return render(request, 'staff/staff_bank_request_detail.html', context)




# ===== スタッフ外国籍情報関連ビュー =====

@login_required
@permission_required('staff.view_staffinternational', raise_exception=True)
def staff_international_detail(request, staff_id):
    """スタッフの外国籍情報詳細表示"""
    staff = get_object_or_404(Staff, pk=staff_id)
    try:
        international = StaffInternational.objects.get(staff=staff)
    except StaffInternational.DoesNotExist:
        # 未登録の場合は登録画面へリダイレクト
        return redirect('staff:staff_international_create', staff_id=staff.pk)

    context = {
        'staff': staff,
        'international': international,
    }
    return render(request, 'staff/staff_international_detail.html', context)


@login_required
@permission_required('staff.add_staffinternational', raise_exception=True)
def staff_international_create(request, staff_id):
    """スタッフの外国籍情報登録"""
    staff = get_object_or_404(Staff, pk=staff_id)
    # 既に登録済みの場合は編集画面へリダイレクト
    if hasattr(staff, 'international'):
        return redirect('staff:staff_international_edit', staff_id=staff.pk)

    if request.method == 'POST':
        form = StaffInternationalForm(request.POST)
        if form.is_valid():
            international = form.save(commit=False)
            international.staff = staff
            international.save()
            messages.success(request, '外国籍情報を登録しました。')
            return redirect('staff:staff_international_detail', staff_id=staff.pk)
    else:
        form = StaffInternationalForm()

    context = {
        'form': form,
        'staff': staff,
        'is_new': True,
    }
    return render(request, 'staff/staff_international_form.html', context)


@login_required
@permission_required('staff.change_staffinternational', raise_exception=True)
def staff_international_edit(request, staff_id):
    """スタッフの外国籍情報編集"""
    staff = get_object_or_404(Staff, pk=staff_id)
    international = get_object_or_404(StaffInternational, staff=staff)

    if request.method == 'POST':
        form = StaffInternationalForm(request.POST, instance=international)
        if form.is_valid():
            form.save()
            messages.success(request, '外国籍情報を更新しました。')
            return redirect('staff:staff_international_detail', staff_id=staff.pk)
    else:
        form = StaffInternationalForm(instance=international)

    context = {
        'form': form,
        'staff': staff,
        'international': international,
        'is_new': False,
    }
    return render(request, 'staff/staff_international_form.html', context)


@login_required
@permission_required('staff.delete_staffinternational', raise_exception=True)
def staff_international_delete(request, staff_id):
    """スタッフの外国籍情報削除確認"""
    staff = get_object_or_404(Staff, pk=staff_id)
    international = get_object_or_404(StaffInternational, staff=staff)

    if request.method == 'POST':
        international.delete()
        messages.success(request, '外国籍情報を削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'international': international,
    }
    return render(request, 'staff/staff_international_confirm_delete.html', context)


@login_required
@permission_required('staff.change_staffinternational', raise_exception=True)
def staff_international_request_detail(request, staff_pk, pk):
    """外国籍情報申請の詳細、承認・却下"""
    from apps.connect.models import ConnectInternationalRequest
    from apps.profile.models import StaffProfile, StaffProfileInternational

    staff = get_object_or_404(Staff, pk=staff_pk)
    international_request = get_object_or_404(ConnectInternationalRequest, pk=pk)

    # 現在のスタッフの外国籍情報を取得（StaffInternationalモデルから）
    current_international = None
    try:
        from apps.staff.models import StaffInternational
        current_international = StaffInternational.objects.get(staff=staff)
    except StaffInternational.DoesNotExist:
        # 現在の外国籍情報が存在しない場合はNoneのまま
        pass

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            # 承認処理
            try:
                # 申請から外国籍情報を取得
                profile_international = international_request.profile_international

                # スタッフの外国籍情報を更新または作成
                from apps.staff.models import StaffInternational
                staff_international, created = StaffInternational.objects.update_or_create(
                    staff=staff,
                    defaults={
                        'residence_card_number': profile_international.residence_card_number,
                        'residence_status': profile_international.residence_status,
                        'residence_period_from': profile_international.residence_period_from,
                        'residence_period_to': profile_international.residence_period_to,
                    }
                )

                # 申請ステータスを更新
                international_request.status = 'approved'
                international_request.save()

                messages.success(request, f'外国籍情報申請を承認し、{staff.name_last} {staff.name_first}の外国籍情報を更新しました。')
            except Exception as e:
                messages.error(request, f'承認処理中にエラーが発生しました: {e}')

        elif action == 'reject':
            # 却下処理 - ステータスのみ変更、プロファイルは削除しない
            international_request.status = 'rejected'
            international_request.save()

            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'update', international_request)
            messages.warning(request, '外国籍情報申請を却下しました。プロファイル情報は保持されます。')

        return redirect('staff:staff_detail', pk=staff.pk)

    context = {
        'staff': staff,
        'international_request': international_request,
        'current_international': current_international,
    }
    return render(request, 'staff/staff_international_request_detail.html', context)
