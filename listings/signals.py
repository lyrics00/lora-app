from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from .models import LoRAImage, Model


def delete_file(fieldfile):
    # Do not delete if file is default
    default_files = [
        "items/default_item_image.png",
        "collections/default_collection_image.jpg",
    ]
    if fieldfile and fieldfile.name and fieldfile.name not in default_files:
        fieldfile.delete(save=False)


# For Model model:
@receiver(pre_delete, sender=Model)
def auto_delete_model_image_on_delete(sender, instance, **kwargs):
    if instance.image:
        delete_file(instance.image)


@receiver(pre_save, sender=Model)
def auto_delete_model_image_on_change(sender, instance, **kwargs):
    if not instance.pk:
        # New instance, nothing to do.
        return
    try:
        old_image = Model.objects.get(pk=instance.pk).image
    except Model.DoesNotExist:
        return
    new_image = instance.image
    if old_image and old_image != new_image:
        delete_file(old_image)


# For LoRAImage model:
@receiver(pre_delete, sender=LoRAImage)
def auto_delete_loraimage_on_delete(sender, instance, **kwargs):
    if instance.image:
        delete_file(instance.image)


@receiver(pre_save, sender=LoRAImage)
def auto_delete_loraimage_on_change(sender, instance, **kwargs):
    if not instance.pk:
        # New instance, nothing to do.
        return
    try:
        old_image = LoRAImage.objects.get(pk=instance.pk).image
    except LoRAImage.DoesNotExist:
        return
    new_image = instance.image
    if old_image and old_image != new_image:
        delete_file(old_image)
