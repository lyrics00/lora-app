from django.shortcuts import render
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from .forms import ContactForm
def lora_resources(request):
    return render(request, 'resource/lora.html')
def lora_colab_guide(request):
    return render(request, 'resource/lora_colab_guide.html')

from django.shortcuts import render

from django.contrib import messages  # at the top

def help_page(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = f"LoRA Help Request from {form.cleaned_data['name']}"
            message = f"{form.cleaned_data['message']}\n\nFrom: {form.cleaned_data['email']}"
            send_mail(subject, message, 'projectb15.cs3240@gmail.com', ['projectb15.cs3240@gmail.com'])
            messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
            return redirect('help_page')
    else:
        form = ContactForm()
    return render(request, 'resource/help.html', {'form': form})


from django.shortcuts import render

def faq_page(request):
    faqs = [
        {"question": "How do I upload a LoRA model?", "answer": "Go to the LoRA Resources page and use the upload form at the bottom."},
        {"question": "Where are uploaded models stored?", "answer": "Models are securely stored on Amazon S3 and accessible only through authenticated access."},
        {"question": "What file format should my model be?", "answer": "We currently support .safetensors and .pt formats."},
        {"question": "How many images should I use to train a LoRA model?", "answer": "We recommend at least 30–100 quality images with relevant captions."},
        {"question": "Do I need to caption every image?", "answer": "Captions improve results, but uncaptions can still work if prompts are strong."},
        {"question": "What resolution should my training images be?", "answer": "Use 512x512 resolution for best compatibility unless otherwise noted."},
        {"question": "What tools are supported for training?", "answer": "We support Kohya Trainer, Hugging Face Diffusers, and our Colab notebook."},
        {"question": "What is the recommended learning rate?", "answer": "Start with 1e-4 to 5e-5. Too high can overfit; too low may undertrain."},
        {"question": "Can I delete my uploaded model?", "answer": "Yes, you can request deletion through the Contact Us form."},
        {"question": "What is a LoRA rank?", "answer": "LoRA rank defines how much of the base model’s weights are adapted. Common values: 4, 8, 16."},
        {"question": "Can I fine-tune LoRAs for specific characters?", "answer": "Absolutely. Just ensure diverse, relevant image samples."},
        {"question": "What’s the difference between LoRA and Dreambooth?", "answer": "LoRA is lighter and more efficient. Dreambooth fine-tunes the full model."},
        {"question": "Why does my trained LoRA look blurry?", "answer": "Check your training resolution, dataset quality, and overfitting."},
        {"question": "Do I need a GPU to train?", "answer": "Yes, training requires a GPU. Google Colab provides free access to one."},
        {"question": "What’s the average training time?", "answer": "On Colab, ~30 minutes for basic training. Depends on dataset and settings."},
        {"question": "Where can I find datasets?", "answer": "Check out our Resources section or browse huggingface.co for open datasets."},
        {"question": "Can I make my model public?", "answer": "Yes! Just note that once public, it's accessible by others."},
        {"question": "How can I test my LoRA model?", "answer": "Use interfaces like AUTOMATIC1111 or ComfyUI with your base model and LoRA."},
        {"question": "What base model should I use?", "answer": "SD 1.5 is common. Match it with your LoRA training config."},
        {"question": "Are there legal concerns with training on certain data?", "answer": "Yes. Avoid copyrighted, private, or sensitive data."},
    ]
    return render(request, 'resource/faq.html', {'faqs': list(enumerate(faqs))})
