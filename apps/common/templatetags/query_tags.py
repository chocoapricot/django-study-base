from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    リクエストのGETクエリパラメータを更新し、URLエンコードされた文字列を返す。
    """
    # コンテキストからリクエストオブジェクトを取得
    request = context.get('request')
    if not request:
        return ''

    # 現在のGETパラメータをコピー
    query_params = request.GET.copy()

    # kwargsで渡されたパラメータで更新
    for key, value in kwargs.items():
        query_params[key] = value

    # URLエンコードして返す
    return query_params.urlencode()
