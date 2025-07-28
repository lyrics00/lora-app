from django.shortcuts import render

def help_page(request):
    return render(request, "support/help.html")
