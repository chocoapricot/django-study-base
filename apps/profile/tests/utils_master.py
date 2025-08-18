from apps.master.models import Qualification, Skill

def create_test_qualification(name='テスト資格'):
    # 親カテゴリを作成
    parent = Qualification.objects.create(name='テストカテゴリ', level=1, is_active=True)
    # 資格本体
    return Qualification.objects.create(name=name, level=2, parent=parent, is_active=True)

def create_test_skill(name='テスト技能'):
    # 親カテゴリを作成
    parent = Skill.objects.create(name='テストカテゴリ', level=1, is_active=True)
    # 技能本体
    return Skill.objects.create(name=name, level=2, parent=parent, is_active=True)
