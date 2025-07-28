from django.db import migrations

def fix_duplicate_emails(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    
    # First, fix blank emails:
    for user in CustomUser.objects.filter(email=""):
        user.email = f"{user.username}@example.com"
        user.save()

    # Now fix duplicates:
    seen = {}
    # Ensure consistent ordering so the first occurrence remains unchanged.
    for user in CustomUser.objects.all().order_by('pk'):
        email = user.email
        if email in seen:
            # Modify the email to make it unique—appending the primary key or a counter.
            user.email = f"{email.split('@')[0]}+{user.pk}@{email.split('@')[1]}"
            user.save()
        else:
            seen[email] = user.pk

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_customuser_email_alter_customuser_image'),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_emails, reverse_code=migrations.RunPython.noop),
    ]