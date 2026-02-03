from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()

@register.simple_tag(takes_context=True)
def favorite_star(context, obj, size='0.9rem', as_link=False):
    if not obj:
        return ''

    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return ''

    if context.get('hide_favorite'):
        return ''

    model_name = obj.__class__.__name__

    # Check if is_favorite is already annotated
    is_favorite = getattr(obj, 'is_favorite', None)

    if is_favorite is None:
        cache_attr = f'_{model_name.lower()}_favorites_cache'
        if not hasattr(request, cache_attr):
            if model_name == 'Staff':
                from apps.staff.models import StaffFavorite
                setattr(request, cache_attr, set(
                    StaffFavorite.objects.filter(user=request.user).values_list('staff_id', flat=True)
                ))
            elif model_name == 'Client':
                from apps.client.models import ClientFavorite
                setattr(request, cache_attr, set(
                    ClientFavorite.objects.filter(user=request.user).values_list('client_id', flat=True)
                ))
            else:
                return ''

        cache = getattr(request, cache_attr)
        is_favorite = obj.pk in cache

    if is_favorite:
        if as_link:
            if model_name == 'Staff':
                url = reverse('staff:staff_favorite_remove', args=[obj.pk])
            elif model_name == 'Client':
                url = reverse('client:client_favorite_remove', args=[obj.pk])
            else:
                return ''

            return format_html(
                '<a href="{}" class="text-decoration-none" data-bs-toggle="tooltip" data-bs-placement="top" title="お気に入り解除" onclick="return confirm(\'お気に入りを解除しますか？\');">'
                '<i class="bi bi-star-fill text-warning ms-1" style="font-size: {}; cursor: pointer;"></i>'
                '</a>',
                url, size
            )
        else:
            return format_html('<i class="bi bi-star-fill text-warning ms-1" style="font-size: {};"></i>', size)
    return ''
