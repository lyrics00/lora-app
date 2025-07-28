from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages

@login_required
def choose_role(request):
    if request.method == "POST":
        role = request.POST.get("role")
        if role in ["patron", "librarian"]:
            request.user.role = role
            request.user.save()
            return redirect("dashboard")
        # If role is not valid, simply reload the form.
        return redirect("choose_role")
    return render(request, "choose_role.html")
    
@login_required
def patron(request):
    return render(request, "patron.html", {"user": request.user})

@login_required
def librarian(request):
    return render(request, "librarian.html", {"user": request.user})
    
@login_required
def dashboard(request):
    user = request.user
    if user.role == "librarian" or user.role == "patron":
        target_url = reverse('home')
    else:
        # If no role is set, send them to choose_role.
        return redirect("choose_role")
    # Instead of immediately redirecting, render an intermediate page.
    return render(request, "role_redirect.html", {"target_url": target_url})

def home(request):
    return render(request, "home.html", {"user" : request.user})

@login_required
def settings(request):
    return render(request, "account/settings.html", {"user": request.user})

@login_required
def switch_roles(request):
    return render(request, "account/switch_roles.html", {"user": request.user})
@login_required
def switch_role_librarian(request):
    # Update the user's role to 'librarian'
    request.user.role = 'librarian'
    request.user.save()
    messages.success(request, "Your role has been switched to Librarian.")
    return redirect('account_settings')


@login_required
def switch_role_patron(request):
    # Update the user's role to 'patron'
    request.user.role = 'patron'
    request.user.save()
    messages.success(request, "Your role has been switched to Patron.")
    return redirect('account_settings')