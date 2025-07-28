from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ProfileEditForm
from django.conf import settings  # if needed for the default image

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ProfileEditForm

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            profile = form.save(commit=False)
            # Check for the "clear" action or empty file
            if 'image-clear' in request.POST:
                profile.image = 'profile_pics/default_profile.jpg'
            profile.save()
            return redirect('account_settings')  # Adjust redirect as needed
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'profile_edit.html', {'form': form})