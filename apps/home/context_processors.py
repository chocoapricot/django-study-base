from datetime import timedelta
from django.utils import timezone
from apps.staff.models import StaffContactSchedule
from apps.client.models import ClientContactSchedule

def contact_schedule_counts(request):
    """
    ベースヘッダーのアラームアイコンに表示する、昨日と今日の予定数を取得する
    """
    if not request.user.is_authenticated:
        return {}
    
    # 閲覧権限チェック
    has_staff_perm = request.user.has_perm('staff.view_staffcontactschedule')
    has_client_perm = request.user.has_perm('client.view_clientcontactschedule')
    
    if not (has_staff_perm or has_client_perm):
        return {}

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    target_dates = [yesterday, today]
    
    # 昨日と今日の予定数を集計
    counts = 0
    if has_staff_perm:
        counts += StaffContactSchedule.objects.filter(contact_date__in=target_dates).count()
    if has_client_perm:
        counts += ClientContactSchedule.objects.filter(contact_date__in=target_dates).count()
        
    return {'contact_schedule_yesterday_today_count': counts}

def flag_counts(request):
    """
    ベースヘッダーのフラッグアイコンに表示する、フラッグ総数を取得する
    """
    if not request.user.is_authenticated:
        return {}

    from apps.staff.models_other import StaffFlag
    from apps.client.models import ClientFlag
    from apps.contract.models import ContractClientFlag, ContractStaffFlag, ContractAssignmentFlag

    count = (
        StaffFlag.objects.count() +
        ClientFlag.objects.count() +
        ContractClientFlag.objects.count() +
        ContractStaffFlag.objects.count() +
        ContractAssignmentFlag.objects.count()
    )
    return {'total_flag_count': count}
