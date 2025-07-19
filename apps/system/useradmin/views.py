
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import UserProfileForm

@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('useradmin:profile')
    else:
        form = UserProfileForm(instance=user)
    return render(request, 'useradmin/profile.html', {'form': form})
