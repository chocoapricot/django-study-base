from django import template
from ..models import ClientContractPrint

register = template.Library()

@register.filter
def get_latest_quotation(issue_history):
    """
    発行履歴から最新の見積書を取得する。
    """
    return issue_history.filter(print_type=ClientContractPrint.PrintType.QUOTATION).first()

@register.filter
def get_latest_clash_day_notification(issue_history):
    """
    発行履歴から最新の抵触日通知書を取得する。
    """
    return issue_history.filter(print_type=ClientContractPrint.PrintType.CLASH_DAY_NOTIFICATION).first()

@register.filter
def get_latest_dispatch_notification(issue_history):
    """
    発行履歴から最新の派遣通知書を取得する。
    """
    return issue_history.filter(print_type=ClientContractPrint.PrintType.DISPATCH_NOTIFICATION).first()
