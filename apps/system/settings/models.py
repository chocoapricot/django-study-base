from django import forms
from django.db import models
from django.conf import settings

from apps.common.models import MyModel

# Create your models here.
class Dropdowns(MyModel):
    """
    アプリケーション全体で使用されるドロップダウンリストの選択肢を管理するモデル。
    カテゴリ別に選択肢をグループ化し、動的なプルダウンメニューを生成するために使用される。
    """
    category = models.CharField('カテゴリ',max_length=50, default='')  # カテゴリーを文字列として管理
    name = models.CharField('表示名',max_length=100)  # 表示名
    value = models.CharField('設定値',max_length=100)  # 実際の設定値
    disp_seq = models.PositiveIntegerField('表示順',default=0)  # 表示順
    active = models.BooleanField('有効',default=True)  # 表示非表示

    class Meta:
        ordering = ['category','disp_seq']  # 表示順に並べる
        db_table = 'apps_system_dropdowns'  # 既存のテーブル名を指定
        verbose_name = 'プルダウン'
        verbose_name_plural = 'プルダウン'

    def __str__(self):
        return self.name

    @classmethod
    def get_display_name(cls, category, value):
        """指定されたカテゴリと値に対応する表示名を取得する"""
        if not value:
            return ''
        try:
            dropdown = cls.objects.get(category=category, value=value, active=True)
            return dropdown.name
        except cls.DoesNotExist:
            return value  # 見つからない場合は値をそのまま返す

    @classmethod
    def get_choices(cls, category, include_empty=True):
        """指定されたカテゴリの選択肢リストを取得する"""
        choices = []
        if include_empty:
            choices.append(('', '---------'))

        dropdowns = cls.objects.filter(category=category, active=True).order_by('disp_seq')
        choices.extend([(d.value, d.name) for d in dropdowns])
        return choices


class Parameter(MyModel):
    """
    アプリケーション全体で使用される設定値を管理するモデル。
    システム設定や定数などをデータベースで管理するために使用される。
    """
    category = models.CharField('分類',max_length=50, default='')  # カテゴリー
    key = models.CharField('キー',max_length=100)  # 表示名
    value = models.CharField('設定値',max_length=100)  # 実際の設定値
    default_value = models.CharField('初期値',max_length=100)  # 実際の設定値
    note  = models.CharField('備考',max_length=100)  # 実際の設定値
    disp_seq = models.PositiveIntegerField('表示順',default=0)  # 表示順
    active = models.BooleanField('有効',default=True)  # 表示非表示

    class Meta:
        ordering = ['category','disp_seq']  # 表示順に並べる
        db_table = 'apps_system_parameter'  # 既存のテーブル名を指定
        verbose_name = 'パラメータ'
        verbose_name_plural = 'パラメータ'

    def __str__(self):
        return self.key


class Menu(MyModel):
    """
    ナビゲーションメニューの項目を管理するモデル。
    階層構造を持ち、表示順やアクセス権限を設定できる。
    """
    name = models.CharField('表示名',max_length=100)  # 表示名
    url  = models.CharField('URL',max_length=100)  # 実際の設定値
    icon = models.CharField('アイコン',max_length=100)  # 実際の設定値
    icon_style = models.CharField('アイコンスタイル',max_length=100)  # 実際の設定値
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name='親メニュー')  # 階層構造
    level = models.PositiveIntegerField('階層レベル', default=0)  # 階層レベル（0=トップレベル）
    exact_match = models.BooleanField('完全一致', default=False, help_text='URLの完全一致判定を行う')  # URL判定方法
    required_permission = models.CharField('必要な権限', max_length=100, blank=True, null=True, help_text='例: staff.view_staff (空欄の場合は全員アクセス可能)')  # 必要な権限
    disp_seq = models.PositiveIntegerField('表示順',default=0)  # 表示順
    active = models.BooleanField('有効',default=True)  # 表示非表示

    class Meta:
        ordering = ['level', 'disp_seq']  # 階層レベル、表示順に並べる
        db_table = 'apps_system_menu'  # 既存のテーブル名を指定
        verbose_name = 'メニュー'
        verbose_name_plural = 'メニュー'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def is_active_for_path(self, request_path):
        """指定されたパスでこのメニューがアクティブかどうかを判定"""
        # ホームメニュー（/）の特別処理
        if self.url == '/':
            return request_path == '/' or request_path == ''
        
        if self.exact_match:
            # 完全一致の場合でも、そのメニュー配下のページではアクティブにする
            # 例: /client/ メニューは /client/client/detail/11/ でもアクティブ
            menu_url = self.url.rstrip('/')
            request_url = request_path.rstrip('/')
            
            # 完全一致
            if request_url == menu_url:
                return True
            
            # メニュー配下のページかチェック（より具体的なメニューが存在しない場合のみ）
            if request_path.startswith(self.url):
                # より具体的なメニューが存在するかチェック
                from django.db import models
                more_specific_menus = Menu.objects.filter(
                    models.Q(url__startswith=self.url) & ~models.Q(url=self.url),
                    active=True
                )
                
                for specific_menu in more_specific_menus:
                    if specific_menu.is_active_for_path(request_path):
                        return False  # より具体的なメニューがアクティブなので、このメニューは非アクティブ
                
                return True  # より具体的なメニューがないので、このメニューをアクティブにする
            
            return False
        else:
            # 部分一致の場合（従来の動作）
            return self.url in request_path
    
    def get_children(self):
        """子メニューを取得"""
        return Menu.objects.filter(parent=self, active=True).order_by('disp_seq')
    
    @property
    def has_children(self):
        """子メニューがあるかどうか"""
        return self.get_children().exists()
    
    def has_permission(self, user):
        """ユーザーがこのメニューにアクセスする権限があるかチェック"""
        if not user.is_authenticated:
            return False
        
        # スーパーユーザーは全てのメニューにアクセス可能
        if user.is_superuser:
            return True
        
        # 権限が設定されていない場合は全員アクセス可能
        if not self.required_permission:
            return True
        
        # 権限をチェック
        return user.has_perm(self.required_permission)