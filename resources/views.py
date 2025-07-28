from django.shortcuts import render

def resources_page(request):
    return render(request, "resources.html")
