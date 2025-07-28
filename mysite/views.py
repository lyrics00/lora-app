from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from listings.models import LoRA, LoRAImage, Model, Comment, LoRARating
import os

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
        target_url = redirect("choose_role")
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

@login_required
def notifications_page(request):
    # Retrieve all notifications for the current user.
    notifications = request.user.notifications.all()
    context = {
        "notifications": notifications,
    }
    return render(request, "notifications_page.html", context)

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json

MODEL_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"
HEADERS = {
    "Authorization": f"Bearer {settings.HF_API_TOKEN}"
}

@csrf_exempt
def chatbot_response(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")

        payload = {
            "inputs": user_message
        }

        try:
            res = requests.post(MODEL_URL, headers=HEADERS, json=payload)
            res_json = res.json()

            if isinstance(res_json, list) and res_json and "generated_text" in res_json[0]:
                reply = res_json[0]["generated_text"]
            elif "generated_text" in res_json:
                reply = res_json["generated_text"]
            elif "error" in res_json:
                return JsonResponse({"error": res_json["error"]}, status=500)
            else:
                reply = res_json.get("error", "Sorry, I couldn't understand that.")

            return JsonResponse({"reply": reply})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def chatbot_gemini(request):
    """
    Chatbot view using Google Gemini API.
    Expects POST with JSON: {"message": "..."}
    Passes app context, user info, and rules to the model.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "")
            api_key = os.environ.get("GEMINI_API_KEY")

            # Get counts and sample titles
            lora_count = LoRA.objects.count()
            model_count = Model.objects.count()
            lora_titles = list(LoRA.objects.values_list('title', flat=True)[:5])
            model_titles = list(Model.objects.values_list('title', flat=True)[:5])

            # Extra context: include up to 10 items/models with URLs and descriptions
            item_context = ""
            for lora in LoRA.objects.all()[:10]:
                full_url = f"{request.scheme}://{request.get_host()}/listings/lora/{lora.id}/"
                item_context += f"- {lora.title} (ID: {lora.id}, URL: {full_url}, Desc: {lora.description[:60]}...)\n"

            model_context = ""
            for model in Model.objects.all()[:10]:
                full_url = f"{request.scheme}://{request.get_host()}/listings/model/{model.id}/"
                model_context += f"- {model.title} (ID: {model.id}, URL: {full_url}, Desc: {model.description[:60]}...)\n"

            extra_context = (
                f"Sample items:\n{item_context}\n"
                f"Sample models/collections:\n{model_context}\n"
                "You can suggest these items or models to users by name or the full URL."
            )

            # User info
            if request.user.is_authenticated:
                user_info = (
                    f"Username: {request.user.username}, "
                    f"Role: {getattr(request.user, 'role', 'unknown')}, "
                    f"Email: {request.user.email}"
                )
            else:
                user_info = "Anonymous user"

            # Get current context from the conversation (if any)
            conversation_context = data.get("context", "")

            # Rules and requirements (summarized for context)
            rules = (
                "You are an assistant for the LoRA Market web app, a class project CLA system. "
                "Models are equivalent to collections and LoRAs are equivalent to items. "
                "There are four user types: Anonymous, Patron, Librarian, and Django Administrator. "
                "Anonymous users can browse public items and collections but cannot borrow, rate, or comment. "
                "Patrons can log in with Google, request to borrow items, create public collections, and request access to private collections. "
                "Librarians can add/edit/delete items and collections, approve/deny borrow requests, and upgrade patrons. "
                "Django Administrators only access the admin page. "
                "All uploads are stored on Amazon S3. "
                "Do not share personal information. Only answer questions related to the app, its listings, models, and usage. "
                "If you don't know the answer, say so. Always adhere to these rules."
            )

            # Compose system/context prompt
            context_prompt = (
                f"{rules}\n\n"
                f"App data:\n"
                f"- {lora_count} LoRA items (e.g., {', '.join(lora_titles)})\n"
                f"- {model_count} Models/Collections (e.g., {', '.join(model_titles)})\n"
                f"{extra_context}\n"
                f"User info: {user_info}\n"
                f"Conversation context: {conversation_context}\n"
                f"User message: {user_message}"
            )

            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "contents": [
                    {"parts": [{"text": context_prompt}]}
                ]
            }
            params = {"key": api_key}
            response = requests.post(url, headers=headers, params=params, json=payload, timeout=15)
            res_json = response.json()

            # Parse Gemini response
            reply = (
                res_json.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "Sorry, I couldn't understand that.")
            )

            return JsonResponse({"reply": reply})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400)

# In views.py
def account_settings_view(request):
    return render(request, 'account/settings.html')

