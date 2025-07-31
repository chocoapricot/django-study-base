from allauth.account.views import SignupView
from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import CustomSignupForm

class CustomSignupView(SignupView):
    form_class = CustomSignupForm

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('agreed_to_terms', False):
            return redirect(reverse('terms_of_service'))
        return super().dispatch(request, *args, **kwargs)

def terms_of_service(request):
    if request.method == 'POST':
        if request.POST.get('agree_to_terms'):
            request.session['agreed_to_terms'] = True
            return redirect(reverse('account_signup'))
        else:
            # 同意しなかった場合、セッションをクリアして再度同意を求める
            request.session['agreed_to_terms'] = False
            return render(request, 'account/terms_of_service.html', {'error': 'サービス利用規約に同意してください。'})
    # GETリクエストの場合、またはサインアップページからリダイレクトされた場合
    # セッションのagreed_to_termsフラグをクリアして、常に同意画面を表示する
    request.session['agreed_to_terms'] = False
    return render(request, 'account/terms_of_service.html')