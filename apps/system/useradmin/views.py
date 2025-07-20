
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from .forms import UserProfileForm

@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            obj = form.save(commit=False)
            pw = form.cleaned_data.get('password')
            if pw:
                obj.set_password(pw)
            obj.save()
            if pw:
                update_session_auth_hash(request, obj)
            return redirect('useradmin:profile')
    else:
        form = UserProfileForm(instance=user)
    return render(request, 'useradmin/profile.html', {'form': form})
