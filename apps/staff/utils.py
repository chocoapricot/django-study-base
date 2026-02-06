# apps/staff/utils.py
from apps.master.models import UserParameter

def get_staff_face_photo_style():
    """
    設定値マスタからスタッフの顔写真表示形式を取得する。
    値が存在しない場合は、デフォルトで "round" を返す。
    """
    try:
        return UserParameter.objects.get(pk="STAFF_FACE_PHOTO_STYLE").value
    except UserParameter.DoesNotExist:
        return "round"

def delete_staff_placeholder(staff_pk):
    """
    スタッフのキャッシュされたプレースホルダー画像を削除する。
    名前や性別が変更された場合、または写真がアップロードされた場合に呼び出す。
    """
    import os
    from django.conf import settings
    placeholder_path = os.path.join(settings.MEDIA_ROOT, 'staff_files', 'placeholders', f"{staff_pk}.jpg")
    if os.path.exists(placeholder_path):
        try:
            os.remove(placeholder_path)
        except Exception:
            pass

def get_annotated_staff_queryset(user):
    """
    スタッフ一覧表示に必要な共通の注釈（次回連絡日、お気に入り等）を付与したクエリセットを返す。
    """
    from django.db.models import OuterRef, Subquery, Exists
    from django.utils import timezone
    from .models import Staff, StaffContactSchedule, StaffFavorite

    next_schedule = StaffContactSchedule.objects.filter(
        staff=OuterRef('pk'),
        contact_date__gte=timezone.localdate()
    ).order_by('contact_date')

    favorites = StaffFavorite.objects.filter(
        staff=OuterRef('pk'),
        user=user
    )

    return Staff.objects.annotate(
        next_contact_date=Subquery(next_schedule.values('contact_date')[:1]),
        next_contact_content=Subquery(next_schedule.values('content')[:1]),
        is_favorite=Exists(favorites)
    )

def annotate_staff_connection_info(staff_list):
    """
    スタッフのリストに対し、接続状況（承認済み、申請中、各申請の有無）の属性を付与する。
    """
    from apps.connect.models import (
        ConnectStaff, MynumberRequest, ProfileRequest, BankRequest,
        ContactRequest, ConnectInternationalRequest, DisabilityRequest
    )
    from apps.company.models import Company

    company = Company.objects.first()
    corporate_number = company.corporate_number if company else None

    staff_emails = [s.email for s in staff_list if s.email]
    connect_staff_map = {}
    pending_requests = {}

    if corporate_number and staff_emails:
        connect_staff_qs = ConnectStaff.objects.filter(
            corporate_number=corporate_number,
            email__in=staff_emails
        )
        connect_staff_map = {cs.email: cs for cs in connect_staff_qs}

        approved_connect_staff_ids = [
            cs.id for cs in connect_staff_map.values() if cs.status == 'approved'
        ]

        if approved_connect_staff_ids:
            pending_requests = {
                'mynumber': set(MynumberRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'profile': set(ProfileRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'bank': set(BankRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'contact': set(ContactRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'international': set(ConnectInternationalRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'disability': set(DisabilityRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
            }

    for staff in staff_list:
        staff.is_connected_approved = False
        staff.has_pending_connection_request = False
        staff.has_pending_mynumber_request = False
        staff.has_pending_profile_request = False
        staff.has_pending_bank_request = False
        staff.has_pending_contact_request = False
        staff.has_pending_international_request = False
        staff.has_pending_disability_request = False

        connect_request = connect_staff_map.get(staff.email)
        if connect_request:
            staff.is_connected_approved = connect_request.status == 'approved'
            staff.has_pending_connection_request = connect_request.status == 'pending'
            if staff.is_connected_approved:
                email = staff.email
                staff.has_pending_mynumber_request = email in pending_requests.get('mynumber', set())
                staff.has_pending_profile_request = email in pending_requests.get('profile', set())
                staff.has_pending_bank_request = email in pending_requests.get('bank', set())
                staff.has_pending_contact_request = email in pending_requests.get('contact', set())
                staff.has_pending_international_request = email in pending_requests.get('international', set())
                staff.has_pending_disability_request = email in pending_requests.get('disability', set())

        # 外国籍・障害者情報の有無
        staff.has_international_info = hasattr(staff, 'international')
        staff.has_disability_info = hasattr(staff, 'disability')
