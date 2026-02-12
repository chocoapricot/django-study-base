from django import template
from django.utils.html import format_html

register = template.Library()

@register.simple_tag
def staff_status_markers(staff):
    if not staff:
        return ''

    html = ''
    # モデルのプロパティまたはビューで動的に設定されたフラグを確認
    is_international = getattr(staff, 'has_international', False) or getattr(staff, 'has_international_info', False)
    is_disability = getattr(staff, 'has_disability', False) or getattr(staff, 'has_disability_info', False)

    if is_international:
        html += '<i class="bi bi-send ms-1" style="color:#17a2b8;" title="外国籍"></i>'
    if is_disability:
        html += '<i class="bi bi-heart ms-1" style="color:#17a2b8;" title="障害者"></i>'

    return format_html(html)

@register.filter
def current_grade_as_of(staff, date):
    """指定日時点の等級を取得するフィルタ"""
    if not staff or not date:
        return None
    return staff.get_current_grade(date)

@register.filter
def duration_until(grade, date):
    """指定日の前日までの継続期間を返すフィルタ"""
    if not grade or not date:
        return ""
    from datetime import timedelta
    return grade.get_duration(date - timedelta(days=1))
