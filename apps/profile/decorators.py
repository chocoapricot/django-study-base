from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.master.models import StaffAgreement

def check_staff_agreement(view_func):
    """
    スタッフが必要な規約にすべて同意しているか確認するデコレータ。
    未同意の規約がある場合、connectアプリの同意画面にリダイレクトする。
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # ログインしていないユーザー、またはis_staffユーザーは対象外
        if not request.user.is_authenticated or request.user.is_staff:
            return view_func(request, *args, **kwargs)

        # ユーザーの承認済み接続を取得
        connections = ConnectStaff.objects.filter(email=request.user.email, status='approved')
        if not connections.exists():
            return view_func(request, *args, **kwargs)

        # 接続ごとに未同意の規約がないかチェック
        for connection in connections:
            required_agreements = StaffAgreement.objects.filter(
                corporation_number=connection.corporate_number,
                is_active=True
            )
            if not required_agreements.exists():
                continue

            agreed_pks = ConnectStaffAgree.objects.filter(
                email=request.user.email,
                corporate_number=connection.corporate_number,
                is_agreed=True
            ).values_list('staff_agreement__pk', flat=True)

            unagreed_agreements = required_agreements.exclude(pk__in=agreed_pks)

            if unagreed_agreements.exists():
                # 未同意の規約があれば、その接続の同意画面にリダイレクト
                return redirect(reverse('connect:staff_agreement_consent', kwargs={'pk': connection.pk}))

        return view_func(request, *args, **kwargs)
    return _wrapped_view
