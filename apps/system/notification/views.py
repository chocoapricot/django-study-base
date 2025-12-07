from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Notification

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notification/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationDetailView(LoginRequiredMixin, DetailView):
    model = Notification
    template_name = 'notification/notification_detail.html'
    context_object_name = 'notification'

    def get_queryset(self):
        # ログインユーザーの通知のみを取得
        return Notification.objects.filter(user=self.request.user)

    def get_object(self, queryset=None):
        # オブジェクトを取得
        notification = super().get_object(queryset)
        # 未読の場合は既読に更新
        if not notification.is_read:
            notification.is_read = True
            notification.save()
        return notification
