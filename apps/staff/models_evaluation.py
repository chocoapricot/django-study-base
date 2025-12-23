from django.db import models
from django.conf import settings
from .models_staff import Staff
from ..common.models import MyModel

class StaffEvaluation(MyModel):
    """
    スタッフの評価を管理するモデル。
    """
    staff = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='evaluations', 
        verbose_name='スタッフ'
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='評価者'
    )
    evaluation_date = models.DateField('評価日', default=models.functions.Now)
    
    # 評価項目
    rating = models.IntegerField(
        '評価', 
        choices=[(i, str(i)) for i in range(1, 6)], 
        default=3,
        help_text='1(悪い) - 5(良い)'
    )
    comment = models.TextField('コメント', blank=True, null=True)

    class Meta:
        db_table = 'apps_staff_evaluation'
        verbose_name = 'スタッフ評価'
        verbose_name_plural = 'スタッフ評価'
        ordering = ['-evaluation_date']

    def __str__(self):
        return f"{self.staff} - {self.evaluation_date} - {self.get_rating_display()}"
