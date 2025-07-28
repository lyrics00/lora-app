import os
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from .models import Collection, ItemImage

def delete_file(fieldfile):
    # Do not delete if file is default
    default_files = ["items/default_item_image.png", "collections/default_collection_image.jpg"]
    if fieldfile and fieldfile.name and fieldfile.name not in default_files:
        fieldfile.delete(save=False)

# For Collection model:
@receiver(pre_delete, sender=Collection)
def auto_delete_collection_image_on_delete(sender, instance, **kwargs):
    if instance.image:
        delete_file(instance.image)

@receiver(pre_save, sender=Collection)
def auto_delete_collection_image_on_change(sender, instance, **kwargs):
    if not instance.pk:
        # New instance, nothing to do.
        return
    try:
        old_image = Collection.objects.get(pk=instance.pk).image
    except Collection.DoesNotExist:
        return
    new_image = instance.image
    if old_image and old_image != new_image:
        delete_file(old_image)

# For ItemImage model:
@receiver(pre_delete, sender=ItemImage)
def auto_delete_itemimage_on_delete(sender, instance, **kwargs):
    if instance.image:
        delete_file(instance.image)

@receiver(pre_save, sender=ItemImage)
def auto_delete_itemimage_on_change(sender, instance, **kwargs):
    if not instance.pk:
        # New instance, nothing to do.
        return
    try:
        old_image = ItemImage.objects.get(pk=instance.pk).image
    except ItemImage.DoesNotExist:
        return
    new_image = instance.image
    if old_image and old_image != new_image:
        delete_file(old_image)