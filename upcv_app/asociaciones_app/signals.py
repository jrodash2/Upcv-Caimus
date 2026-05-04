from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def ensure_superadmin_group(sender, **kwargs):
    if sender.name != "asociaciones_app":
        return
    Group.objects.get_or_create(name="Superadmin")
