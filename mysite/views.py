from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def dashboard(request):
    user = request.user

    # Redirect users based on their role
    if user.role == "librarian":
        return redirect("librarian")
    elif user.role == "patron":
        return redirect("patron")

    # Default if role is not set
    return render(request, "home.html", {"user": user})


@login_required
def patron(request):
    return render(request, "patron.html", {"user": request.user})


@login_required
def librarian(request):
    return render(request, "librarian.html", {"user": request.user})
