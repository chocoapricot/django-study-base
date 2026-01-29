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
