from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from patron_requests.models import BorrowedItem

class Command(BaseCommand):
    help = "Send reminder emails for borrowed items due within the next 24 hours"

    def handle(self, *args, **options):
        now = timezone.now()
        threshold = now + timezone.timedelta(hours=24)
        due_soon_items = BorrowedItem.objects.filter(due_date__lte=threshold, due_date__gte=now, reminder_sent=False)
        
        for borrowed in due_soon_items:
            subject = f"Reminder: {borrowed.item.title} is due soon"
            message = (
                f"Dear {borrowed.patron.username},\n\n"
                f"Your borrowed item '{borrowed.item.title}' is due on {borrowed.due_date.strftime('%Y-%m-%d %H:%M')}. "
                "Please return it on time.\n\nThank you."
            )
            recipient = [borrowed.patron.email]
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient)
                borrowed.reminder_sent = True
                borrowed.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Sent reminder for {borrowed.item.title} to {borrowed.patron.email}."
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed to send reminder for {borrowed.item.title} to {borrowed.patron.email}: {e}"
                ))