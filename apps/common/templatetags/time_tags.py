from django import template

register = template.Library()


@register.filter
def format_time_with_next_day(time_obj, is_next_day):
    """
    時刻を翌日フラグ付きでフォーマットする
    
    使用例:
    {{ work_time.start_time|format_time_with_next_day:work_time.start_time_next_day }}
    """
    if not time_obj:
        return ''
    
    time_str = time_obj.strftime('%H:%M')
    
    if is_next_day:
        return f'翌{time_str}'
    
    return time_str
