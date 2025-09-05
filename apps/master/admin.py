from django.contrib import admin
from .models import MailTemplate

@admin.register(MailTemplate)
class MailTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_key', 'subject', 'remarks')
    search_fields = ('template_key', 'subject', 'body', 'remarks')
    list_filter = ('template_key',)
    ordering = ('template_key',)