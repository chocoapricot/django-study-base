from django import template
from ..models import ClientContractPrint

register = template.Library()

@register.filter
def get_latest_quotation(issue_history):
    """
    発行履歴から最新の見積書を取得する。
    """
    return issue_history.filter(print_type=ClientContractPrint.PrintType.QUOTATION).first()
