from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class MyPasswordRules(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        #print(f"[DEBUG] MyPasswordRules.authenticate called with username={username}")
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
            #print(f"[DEBUG] Found user: {user}, is_active: {user.is_active}")
        except UserModel.DoesNotExist:
            return None
        
        if user.check_password(password):
            #print(f"[DEBUG] Password check passed for user: {user}")
            # is_activeチェックを追加
            if user.is_active:
                #print(f"[DEBUG] User is active, returning user")
                return user
            else:
                #print(f"[DEBUG] User is not active, returning None")
                return None
        else:
            #print(f"[DEBUG] Password check failed for user: {user}")
            return None
