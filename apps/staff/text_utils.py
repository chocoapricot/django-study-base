
def generate_staff_evaluations_full_text(staff):
    """
    スタッフのすべての評価を一つのテキストにまとめる。
    """
    evaluations = staff.evaluations.all().order_by('evaluation_date')

    if not evaluations:
        return "このスタッフにはまだ評価がありません。"

    full_text = f"スタッフ名: {staff.name_last} {staff.name_first} の評価一覧\n\n"

    for eval in evaluations:
        full_text += f"評価日: {eval.evaluation_date.strftime('%Y-%m-%d')}\n"
        full_text += f"評価: {eval.get_rating_display()} ★\n"
        full_text += f"コメント:\n{eval.comment or 'コメントなし'}\n"
        full_text += "---\n"

    return full_text
