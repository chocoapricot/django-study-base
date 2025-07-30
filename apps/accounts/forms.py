from django import forms
from allauth.account.forms import SignupForm

class CustomSignupForm(SignupForm):
    last_name = forms.CharField(max_length=30, label='姓')
    first_name = forms.CharField(max_length=30, label='名')

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.last_name = self.cleaned_data['last_name']
        user.first_name = self.cleaned_data['first_name']
        user.save()
        return user
