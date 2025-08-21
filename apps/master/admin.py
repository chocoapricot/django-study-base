from django.contrib import admin
from .models import Qualification, Skill, BillPayment, BillBank

# 資格マスタ、技能マスタ、支払いサイト、会社銀行は
# Webインターフェースで管理するため、admin.pyには登録しない