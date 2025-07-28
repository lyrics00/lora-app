from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from .forms import ContactForm

def lora_resources(request):
    return render(request, 'resource/lora.html')
def lora_colab_guide(request):
    return render(request, 'resource/lora_colab_guide.html')

def gettingstarted_page(request):
    form = ContactForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        subject = f"LoRA Help Request from {form.cleaned_data['name']}"
        message = f"{form.cleaned_data['message']}\n\nFrom: {form.cleaned_data['email']}"
        send_mail(subject, message, 'projectb15.cs3240@gmail.com', ['projectb15.cs3240@gmail.com'])
        messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
        return redirect('gettingstarted_page')

    faqs = [
        {
            "question": "How do I upload a LoRA model?",
            "answer": "Go to the LoRA Resources page and use the upload form at the bottom."
        },
        {
            "question": "Where are uploaded models stored?",
            "answer": "Models are securely stored on Amazon S3 and accessible only through authenticated access."
        },
        {
            "question": "What file format should my model be?",
            "answer": "We currently support .safetensors and .pt formats."
        },
        {
            "question": "How many images should I use to train a LoRA model?",
            "answer": "We recommend at least 30–100 quality images with relevant captions."
        },
        {
            "question": "Do I need to caption every image?",
            "answer": "Captions improve results, but uncaptions can still work if prompts are strong."
        },
        {
            "question": "What resolution should my training images be?",
            "answer": "Use 512x512 resolution for best compatibility unless otherwise specified."
        },
        {
            "question": "Can I fine-tune my model after uploading?",
            "answer": "Not directly. You can download your model, retrain it, and upload a new version."
        },
        {
            "question": "How do I delete a model I uploaded?",
            "answer": "Go to your profile, view your uploads, and use the delete option next to the model."
        },
        {
            "question": "Is there a file size limit for uploads?",
            "answer": "Yes, the maximum file size is currently 1GB."
        },
        {
            "question": "Can I upload multiple models at once?",
            "answer": "Batch uploads are not yet supported. Please upload models one at a time."
        },
        {
            "question": "Why did my upload fail?",
            "answer": "Common reasons include unsupported formats, exceeding file size, or internet interruptions."
        },
        {
            "question": "Can I share my LoRA model publicly?",
            "answer": "Yes, when uploading, choose 'public' visibility to allow others to access it."
        },
        {
            "question": "What permissions are required to upload?",
            "answer": "You must be logged in and verified to upload models."
        },
        {
            "question": "Are LoRA models reviewed before going public?",
            "answer": "Yes, public models undergo a quick review for content safety and compliance."
        },
        {
            "question": "Can I use LoRA models in commercial projects?",
            "answer": "It depends on the license associated with the model. Always check before use."
        },
        {
            "question": "How do I cite a model I used?",
            "answer": "Use the citation text provided on the model's detail page."
        },
        {
            "question": "What training frameworks are compatible?",
            "answer": "We support models trained using popular frameworks like PyTorch and diffusers."
        },
        {
            "question": "What happens if I forget to include metadata?",
            "answer": "Metadata helps discovery but is not required. Your model will still upload."
        },
        {
            "question": "Can I preview model performance before download?",
            "answer": "Not currently. We recommend reading user reviews and notes on the model page."
        },
        {
            "question": "Who do I contact for upload support?",
            "answer": "Use the Help form on the Resources page or email support for assistance."
        },
    ]

    return render(request, 'resource/gettingstarted.html', {
        'form': form,
        'faqs': list(enumerate(faqs))
    })


def faq_page(request):
    query = request.GET.get("q", "").strip().lower()

    faqs = [
        {
            "question": "How do I upload a LoRA model?",
            "answer": "Go to the LoRA Resources page and use the upload form at the bottom."
        },
        {
            "question": "Where are uploaded models stored?",
            "answer": "Models are securely stored on Amazon S3 and accessible only through authenticated access."
        },
        {
            "question": "What file format should my model be?",
            "answer": "We currently support .safetensors and .pt formats."
        },
        {
            "question": "How many images should I use to train a LoRA model?",
            "answer": "We recommend at least 30–100 quality images with relevant captions."
        },
        {
            "question": "Do I need to caption every image?",
            "answer": "Captions improve results, but uncaptions can still work if prompts are strong."
        },
        {
            "question": "What resolution should my training images be?",
            "answer": "Use 512x512 resolution for best compatibility unless otherwise specified."
        },
        {
            "question": "Can I fine-tune my model after uploading?",
            "answer": "Not directly. You can download your model, retrain it, and upload a new version."
        },
        {
            "question": "How do I delete a model I uploaded?",
            "answer": "Go to your profile, view your uploads, and use the delete option next to the model."
        },
        {
            "question": "Is there a file size limit for uploads?",
            "answer": "Yes, the maximum file size is currently 1GB."
        },
        {
            "question": "Can I upload multiple models at once?",
            "answer": "Batch uploads are not yet supported. Please upload models one at a time."
        },
        {
            "question": "Why did my upload fail?",
            "answer": "Common reasons include unsupported formats, exceeding file size, or internet interruptions."
        },
        {
            "question": "Can I share my LoRA model publicly?",
            "answer": "Yes, when uploading, choose 'public' visibility to allow others to access it."
        },
        {
            "question": "What permissions are required to upload?",
            "answer": "You must be logged in and verified to upload models."
        },
        {
            "question": "Are LoRA models reviewed before going public?",
            "answer": "Yes, public models undergo a quick review for content safety and compliance."
        },
        {
            "question": "Can I use LoRA models in commercial projects?",
            "answer": "It depends on the license associated with the model. Always check before use."
        },
        {
            "question": "How do I cite a model I used?",
            "answer": "Use the citation text provided on the model's detail page."
        },
        {
            "question": "What training frameworks are compatible?",
            "answer": "We support models trained using popular frameworks like PyTorch and diffusers."
        },
        {
            "question": "What happens if I forget to include metadata?",
            "answer": "Metadata helps discovery but is not required. Your model will still upload."
        },
        {
            "question": "Can I preview model performance before download?",
            "answer": "Not currently. We recommend reading user reviews and notes on the model page."
        },
        {
            "question": "Who do I contact for upload support?",
            "answer": "Use the Help form on the Resources page or email support for assistance."
        },
    ]

    if query:
        faqs = [
            faq for faq in faqs
            if query in faq["question"].lower() or query in faq["answer"].lower()
        ]

    return render(request, 'resource/faq.html', {
        'faqs': list(enumerate(faqs)),
        'query': request.GET.get("q", "")
    })

def dataset_guide(request):
    return render(request, 'resource/dataset_guide.html')

def tuning_guide(request):
    return render(request, 'resource/tuning_guide.html')
def help_page(request):
    form = ContactForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        subject = f"LoRA Help Request from {form.cleaned_data['name']}"
        message = f"{form.cleaned_data['message']}\n\nFrom: {form.cleaned_data['email']}"
        send_mail(subject, message, 'projectb15.cs3240@gmail.com', ['projectb15.cs3240@gmail.com'])
        messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
        return redirect('help_page')
    faqs = [
        {
            "question": "How do I upload a LoRA model?",
            "answer": "Go to the LoRA Resources page and use the upload form at the bottom."
        },
        {
            "question": "Where are uploaded models stored?",
            "answer": "Models are securely stored on Amazon S3 and accessible only through authenticated access."
        },
        {
            "question": "What file format should my model be?",
            "answer": "We currently support .safetensors and .pt formats."
        },
        {
            "question": "How many images should I use to train a LoRA model?",
            "answer": "We recommend at least 30–100 quality images with relevant captions."
        },
        {
            "question": "Do I need to caption every image?",
            "answer": "Captions improve results, but uncaptions can still work if prompts are strong."
        },
        {
            "question": "What resolution should my training images be?",
            "answer": "Use 512x512 resolution for best compatibility unless otherwise specified."
        },
        {
            "question": "Can I fine-tune my model after uploading?",
            "answer": "Not directly. You can download your model, retrain it, and upload a new version."
        },
        {
            "question": "How do I delete a model I uploaded?",
            "answer": "Go to your profile, view your uploads, and use the delete option next to the model."
        },
        {
            "question": "Is there a file size limit for uploads?",
            "answer": "Yes, the maximum file size is currently 1GB."
        },
        {
            "question": "Can I upload multiple models at once?",
            "answer": "Batch uploads are not yet supported. Please upload models one at a time."
        },
        {
            "question": "Why did my upload fail?",
            "answer": "Common reasons include unsupported formats, exceeding file size, or internet interruptions."
        },
        {
            "question": "Can I share my LoRA model publicly?",
            "answer": "Yes, when uploading, choose 'public' visibility to allow others to access it."
        },
        {
            "question": "What permissions are required to upload?",
            "answer": "You must be logged in and verified to upload models."
        },
        {
            "question": "Are LoRA models reviewed before going public?",
            "answer": "Yes, public models undergo a quick review for content safety and compliance."
        },
        {
            "question": "Can I use LoRA models in commercial projects?",
            "answer": "It depends on the license associated with the model. Always check before use."
        },
        {
            "question": "How do I cite a model I used?",
            "answer": "Use the citation text provided on the model's detail page."
        },
        {
            "question": "What training frameworks are compatible?",
            "answer": "We support models trained using popular frameworks like PyTorch and diffusers."
        },
        {
            "question": "What happens if I forget to include metadata?",
            "answer": "Metadata helps discovery but is not required. Your model will still upload."
        },
        {
            "question": "Can I preview model performance before download?",
            "answer": "Not currently. We recommend reading user reviews and notes on the model page."
        },
        {
            "question": "Who do I contact for upload support?",
            "answer": "Use the Help form on the Resources page or email support for assistance."
        },
    ]

    return render(request, 'resource/help.html', {'form': form,'faqs': list(enumerate(faqs))})