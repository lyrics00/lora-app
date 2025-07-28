[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/hLqvXyMi)

# How to run the project locally
Before you get started it is recommended to create a Virtual Environment
bash: python -m venv myenv
bash: source myenv/bin/activate     # macOS/Linux
bash: myenv\Scripts\activate.bat    # Windows


First, Install Dependencies
bash: pip install -r requirements.txt

Then, Run Migrations
bash: python manage.py migrate

Then, Run Server
bash: python manage.py runserver

Finally, you should be able to access the server at: http://127.0.0.1:8000

# What is LoRA Market 

**LoRA Market** is a web platform for uploading, browsing, borrowing, and managing fine-tuned AI models (LoRAs). Users interact with the platform as either **Patrons** or **Librarians**, each with access to different features based on their role.

---

## 🧭 Platform Overview

Upon signing up or logging in, users are directed to the home page with role-specific access:

- **Patrons**: Can browse and borrow LoRA models, view public model details, and submit feedback.
- **Librarians**: Have full control over creating, uploading, editing, and managing LoRA models and responding to patron requests.

---

## 🔐 Authentication

- Login is accessible from the top-right navigation bar.
- Users may sign in with Google (Patron role) or create an account with email and choose the Librarian role.
- Upon successful login, the top navigation bar updates to display the user's role and username.

---

## 📑 Pages and Features

### 1. Getting Started Page

- Gives you the jist of lora, while letting you access some tips/faqs that might better help you understand the purpose.

---

### Help Page

- Accessible from the top navigation bar.
- Includes a contact form for inquiries and a dynamically expandable FAQ section.
- A chatbot is available in the lower-right corner for quick answers to common questions.

---

### 2. LoRA Resources Page

- Lists external tools and documentation related to LoRA model creation and usage.
- Includes downloadable guides and documentation.
- Provides a form for uploading a LoRA resource, including title, description, and file upload.

---

### 3. Create Model Page

- Enables Librarians to create a new model with a title, description, model type (public/private), and an image.
- After creation, the model becomes visible in "Browse Models" and "My LoRAs" (for librarians).

---

### 4. Browse Models Page

- Displays a card-based layout of all public models.
- Users can:
  - View model details
  - Like models
  - Submit a star rating
  - Borrow a model for future use (with date/time selection)
- Librarians can also:
  - Add LoRAs to their models
  - Edit model descriptions directly from the detail view

---

### 5. My LoRAs Page

- Lists all models created by the logged-in Librarian.
- Offers options to:
  - View model details
  - Delete models

---

### 6. Create LoRA Page (Librarians Only)

- Enables Librarians to upload new LoRA instances to associate with existing models.
- Requires title, description, location, and image upload.
- LoRA entries appear under their associated model in "My LoRAs" after submission.

---

### 7. Active LoRA Requests (Librarians Only)

- View and manage incoming borrow requests from Patrons.
- Approve or deny requests.
- Also includes the ability to promote Patron users to Librarian status using their username.

---

### 🔚 Logging Out

- Users may log out from the account icon in the top-right corner of the site.
- This redirects users back to the public-facing home page.

---

## 🛠 Tech Stack

- **Framework**: Django
- **Auth**: Google OAuth + AllAuth
- **Storage**: AWS S3 for media and static files
- **UI**: Bootstrap 5, custom forms
- **Extras**: Integrated chatbot, dynamic ratings, borrowing system

---

## 📁 Project Structure Summary

- `accounts/`: Handles user authentication and roles
- `listings/`: Manages model creation and display
- `resource/`: Handles LoRA uploads and metadata
- `notifications/`: Manages borrow requests and user actions

---


## 🙏 Thank You

Thank you for tuning in with LoRA Market ! Your visit helps us improve the platform and make model sharing easier for everyone.
