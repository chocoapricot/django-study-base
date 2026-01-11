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
