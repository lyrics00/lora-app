from django.shortcuts import render

def lora_resources(request):
    return render(request, 'resource/lora.html')
