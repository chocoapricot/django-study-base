from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.urls import reverse
from .models import StaffProfile, ProfileMynumber, StaffProfileInternational, StaffBankProfile, StaffDisabilityProfile, StaffContact
from .forms import StaffProfileForm, ProfileMynumberForm, StaffProfileInternationalForm, StaffBankProfileForm, StaffDisabilityProfileForm, StaffContactForm


@login_required
@permission_required('profile.view_staffprofile', raise_exception=True)
def profile_detail(request):
    """プロフィール詳細表示"""
    try:
        profile = StaffProfile.objects.get(user=request.user)
    except StaffProfile.DoesNotExist:
        profile = None
    
    context = {
        'profile': profile,
    }
    return render(request, 'profile/profile_detail.html', context)


@login_required
@permission_required('profile.add_staffprofile', raise_exception=True)
@permission_required('profile.change_staffprofile', raise_exception=True)
def profile_edit(request):
    """プロフィール編集"""
    try:
        profile = StaffProfile.objects.get(user=request.user)
        is_new = False
    except StaffProfile.DoesNotExist:
        profile = None
        is_new = True

    if request.method == 'POST':
        form = StaffProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.email = request.user.email
            profile.save()
            
            if is_new:
                messages.success(request, 'プロフィールを作成しました。')
            else:
                messages.success(request, 'プロフィールを更新しました。')
            
            return redirect('profile:detail')
    else:
        if profile is None:
            # 新規作成時はUserの姓・名を初期値にセット
            initial = {
                'name_last': request.user.last_name,
                'name_first': request.user.first_name,
            }
            form = StaffProfileForm(instance=profile, initial=initial)
        else:
            form = StaffProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
        'is_new': is_new,
        'user_email': request.user.email,
    }
    return render(request, 'profile/profile_form.html', context)


@login_required
@permission_required('profile.delete_staffprofile', raise_exception=True)
def profile_delete(request):
    """プロフィール削除確認"""
    profile = get_object_or_404(StaffProfile, user=request.user)
    
    if request.method == 'POST':
        profile.delete()
        messages.success(request, 'プロフィールを削除しました。')
        return redirect('profile:detail')
    
    context = {
        'profile': profile,
    }
    return render(request, 'profile/profile_delete.html', context)


@login_required
@permission_required('profile.view_profilemynumber', raise_exception=True)
def mynumber_detail(request):
    """マイナンバー詳細表示"""
    try:
        mynumber = ProfileMynumber.objects.get(user=request.user)
    except ProfileMynumber.DoesNotExist:
        mynumber = None
    
    context = {
        'mynumber': mynumber,
    }
    return render(request, 'profile/mynumber_detail.html', context)


@login_required
@permission_required('profile.add_profilemynumber', raise_exception=True)
@permission_required('profile.change_profilemynumber', raise_exception=True)
def mynumber_edit(request):
    """マイナンバー編集"""
    try:
        mynumber = ProfileMynumber.objects.get(user=request.user)
        is_new = False
    except ProfileMynumber.DoesNotExist:
        mynumber = None
        is_new = True

    if request.method == 'POST':
        form = ProfileMynumberForm(request.POST, instance=mynumber)
        if form.is_valid():
            mynumber = form.save(commit=False)
            mynumber.user = request.user
            mynumber.email = request.user.email
            mynumber.save()
            
            if is_new:
                messages.success(request, 'マイナンバーを登録しました。')
            else:
                messages.success(request, 'マイナンバーを更新しました。')
            
            return redirect('profile:mynumber_detail')
    else:
        form = ProfileMynumberForm(instance=mynumber)
    
    context = {
        'form': form,
        'mynumber': mynumber,
        'is_new': is_new,
        'user_email': request.user.email,
    }
    return render(request, 'profile/mynumber_form.html', context)


@login_required
@permission_required('profile.delete_profilemynumber', raise_exception=True)
def mynumber_delete(request):
    """マイナンバー削除確認"""
    mynumber = get_object_or_404(ProfileMynumber, user=request.user)
    
    if request.method == 'POST':
        mynumber.delete()
        messages.success(request, 'マイナンバーを削除しました。')
        return redirect('profile:mynumber_detail')
    
    context = {
        'mynumber': mynumber,
    }
    return render(request, 'profile/mynumber_delete.html', context)


@login_required
@permission_required('profile.add_staffprofileinternational', raise_exception=True)
@permission_required('profile.change_staffprofileinternational', raise_exception=True)
def international_edit(request):
    """外国籍情報登録・編集"""
    # 既存の外国籍情報を確認
    try:
        international_profile = StaffProfileInternational.objects.get(user=request.user)
        is_new = False
    except StaffProfileInternational.DoesNotExist:
        international_profile = None
        is_new = True
    
    if request.method == 'POST':
        form = StaffProfileInternationalForm(request.POST, instance=international_profile)
        if form.is_valid():
            # 外国籍情報を保存
            international_profile = form.save(commit=False)
            international_profile.user = request.user
            international_profile.email = request.user.email
            international_profile.save()
            
            # # 接続申請の作成処理
            # from apps.connect.models import ConnectStaff, ConnectInternationalRequest
            # try:
            #     # 承認済みの接続情報を取得
            #     connect_staff = ConnectStaff.objects.filter(
            #         email=request.user.email,
            #         status='approved'
            #     ).first()
                
            #     if connect_staff:
            #         # 既存の申請がない場合のみ作成
            #         existing_request = ConnectInternationalRequest.objects.filter(
            #             connect_staff=connect_staff,
            #             profile_international=international_profile
            #         ).first()
                    
            #         if not existing_request:
            #             ConnectInternationalRequest.objects.create(
            #                 connect_staff=connect_staff,
            #                 profile_international=international_profile,
            #                 status='pending'
            #             )
            # except Exception:
            #     # 接続申請の作成に失敗しても外国籍情報の保存は成功とする
            #     pass
            
            if is_new:
                messages.success(request, '外国籍情報を登録しました。')
            else:
                messages.success(request, '外国籍情報を更新しました。')
            
            return redirect('profile:international_detail')
    else:
        form = StaffProfileInternationalForm(instance=international_profile)
    
    context = {
        'form': form,
        'international_profile': international_profile,
        'is_new': is_new,
    }
    return render(request, 'profile/international_form.html', context)


@login_required
@permission_required('profile.view_staffprofileinternational', raise_exception=True)
def international_detail(request):
    """外国籍情報詳細表示"""
    # 外国籍情報を取得
    try:
        international = StaffProfileInternational.objects.get(user=request.user)
    except StaffProfileInternational.DoesNotExist:
        international = None
    
    context = {
        'international': international,
    }
    return render(request, 'profile/international_detail.html', context)


@login_required
@permission_required('profile.delete_staffprofileinternational', raise_exception=True)
def international_delete(request):
    """外国籍情報削除確認"""
    international = get_object_or_404(StaffProfileInternational, user=request.user)
    
    if request.method == 'POST':
        international.delete()
        messages.success(request, '外国籍情報を削除しました。')
        return redirect('profile:international_detail')
    
    context = {
        'international': international,
    }
    return render(request, 'profile/international_delete.html', context)


@login_required
@permission_required('profile.view_staffbankprofile', raise_exception=True)
def bank_detail(request):
    """銀行口座詳細表示"""
    try:
        bank = StaffBankProfile.objects.get(user=request.user)
    except StaffBankProfile.DoesNotExist:
        bank = None

    context = {
        'bank': bank,
    }
    return render(request, 'profile/bank_detail.html', context)


@login_required
@permission_required('profile.add_staffbankprofile', raise_exception=True)
@permission_required('profile.change_staffbankprofile', raise_exception=True)
def bank_edit(request):
    """銀行口座編集"""
    try:
        bank = StaffBankProfile.objects.get(user=request.user)
        is_new = False
    except StaffBankProfile.DoesNotExist:
        bank = None
        is_new = True

    if request.method == 'POST':
        form = StaffBankProfileForm(request.POST, instance=bank)
        if form.is_valid():
            bank = form.save(commit=False)
            bank.user = request.user
            bank.save()

            # 接続申請の作成処理
            from apps.connect.models import ConnectStaff, BankRequest
            try:
                # 承認済みの接続情報を取得
                connect_staff = ConnectStaff.objects.filter(
                    email=request.user.email,
                    status='approved'
                ).first()

                if connect_staff:
                    # 既存の申請がない場合のみ作成
                    existing_request = BankRequest.objects.filter(
                        connect_staff=connect_staff,
                        profile_bank=bank
                    ).first()

                    if not existing_request:
                        BankRequest.objects.create(
                            connect_staff=connect_staff,
                            profile_bank=bank,
                            status='pending'
                        )
            except Exception:
                # 接続申請の作成に失敗しても処理は継続
                pass

            if is_new:
                messages.success(request, '銀行口座を登録しました。')
            else:
                messages.success(request, '銀行口座を更新しました。')

            return redirect('profile:bank_detail')
    else:
        form = StaffBankProfileForm(instance=bank)

    context = {
        'form': form,
        'bank': bank,
        'is_new': is_new,
    }
    return render(request, 'profile/bank_form.html', context)


@login_required
@permission_required('profile.delete_staffbankprofile', raise_exception=True)
def bank_delete(request):
    """銀行口座削除確認"""
    bank = get_object_or_404(StaffBankProfile, user=request.user)

    if request.method == 'POST':
        bank.delete()
        messages.success(request, '銀行口座を削除しました。')
        return redirect('profile:bank_detail')

    context = {
        'bank': bank,
    }
    return render(request, 'profile/bank_delete.html', context)


@login_required
@permission_required('profile.view_staffdisabilityprofile', raise_exception=True)
def disability_detail(request):
    """障害者情報詳細表示"""
    try:
        disability = StaffDisabilityProfile.objects.get(user=request.user)
    except StaffDisabilityProfile.DoesNotExist:
        disability = None

    context = {
        'disability': disability,
    }
    return render(request, 'profile/disability_detail.html', context)


@login_required
@permission_required('profile.add_staffdisabilityprofile', raise_exception=True)
@permission_required('profile.change_staffdisabilityprofile', raise_exception=True)
def disability_edit(request):
    """障害者情報編集"""
    try:
        disability = StaffDisabilityProfile.objects.get(user=request.user)
        is_new = False
    except StaffDisabilityProfile.DoesNotExist:
        disability = None
        is_new = True

    if request.method == 'POST':
        form = StaffDisabilityProfileForm(request.POST, instance=disability)
        if form.is_valid():
            disability = form.save(commit=False)
            disability.user = request.user
            disability.email = request.user.email
            disability.save()

            if is_new:
                messages.success(request, '障害者情報を登録しました。')
            else:
                messages.success(request, '障害者情報を更新しました。')

            return redirect('profile:disability_detail')
    else:
        form = StaffDisabilityProfileForm(instance=disability)

    context = {
        'form': form,
        'disability': disability,
        'is_new': is_new,
        'user_email': request.user.email,
    }
    return render(request, 'profile/disability_form.html', context)


@login_required
@permission_required('profile.delete_staffdisabilityprofile', raise_exception=True)
def disability_delete(request):
    """障害者情報削除確認"""
    disability = get_object_or_404(StaffDisabilityProfile, user=request.user)

    if request.method == 'POST':
        disability.delete()
        messages.success(request, '障害者情報を削除しました。')
        return redirect('profile:disability_detail')

    context = {
        'disability': disability,
    }
    return render(request, 'profile/disability_delete.html', context)


@login_required
@permission_required('profile.view_staffcontact', raise_exception=True)
def contact_detail(request):
    """スタッフ連絡先情報詳細表示"""
    try:
        contact = StaffContact.objects.get(user=request.user)
    except StaffContact.DoesNotExist:
        contact = None

    context = {
        'contact': contact,
    }
    return render(request, 'profile/contact_detail.html', context)


@login_required
@permission_required('profile.add_staffcontact', raise_exception=True)
@permission_required('profile.change_staffcontact', raise_exception=True)
def contact_edit(request):
    """スタッフ連絡先情報編集"""
    try:
        contact = StaffContact.objects.get(user=request.user)
        is_new = False
    except StaffContact.DoesNotExist:
        contact = None
        is_new = True

    if request.method == 'POST':
        form = StaffContactForm(request.POST, instance=contact)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.user = request.user
            contact.save()

            if is_new:
                messages.success(request, '連絡先情報を登録しました。')
            else:
                messages.success(request, '連絡先情報を更新しました。')

            return redirect('profile:contact_detail')
    else:
        form = StaffContactForm(instance=contact)

    context = {
        'form': form,
        'contact': contact,
        'is_new': is_new,
    }
    return render(request, 'profile/contact_form.html', context)


@login_required
@permission_required('profile.delete_staffcontact', raise_exception=True)
def contact_delete(request):
    """スタッフ連絡先情報削除確認"""
    contact = get_object_or_404(StaffContact, user=request.user)

    if request.method == 'POST':
        contact.delete()
        messages.success(request, '連絡先情報を削除しました。')
        return redirect('profile:contact_detail')

    context = {
        'contact': contact,
    }
    return render(request, 'profile/contact_delete.html', context)
