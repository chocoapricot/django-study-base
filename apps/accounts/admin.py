from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import MyUser

@admin.register(MyUser)
class MyUserAdmin(UserAdmin):
    model = MyUser
    list_display = ('username', 'last_name', 'first_name', 'email', 'is_staff')

    # 一番下だけど追加
    # phone_numberフィールド削除のためfieldsets追加なし