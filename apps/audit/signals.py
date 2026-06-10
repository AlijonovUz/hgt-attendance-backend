from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from apps.utils.models import BaseModel

from .middleware import get_current_ip, get_current_user
from .models import AuditLog


def get_dirty_fields(instance):
    if not instance.pk:
        return {}

    try:
        old_instance = instance.__class__.objects.get(pk=instance.pk)
        old_dict = model_to_dict(old_instance)
        new_dict = model_to_dict(instance)

        dirty_fields = {}
        for field, value in new_dict.items():
            if field in old_dict and old_dict[field] != value:
                old_val = str(old_dict[field]) if old_dict[field] is not None else None
                new_val = str(value) if value is not None else None
                if old_val != new_val:
                    dirty_fields[field] = {"old": old_val, "new": new_val}
        return dirty_fields
    except instance.__class__.DoesNotExist:
        return {}


@receiver(pre_save)
def capture_old_values(sender, instance, **kwargs):
    from apps.users.models import User

    if not (issubclass(sender, BaseModel) or sender == User):
        return
    instance._dirty_fields = get_dirty_fields(instance)


@receiver(post_save)
def audit_log_save(sender, instance, created, **kwargs):
    from apps.users.models import User

    if not (issubclass(sender, BaseModel) or sender == User):
        return

    if sender == AuditLog:
        return

    user = get_current_user()
    ip = get_current_ip()

    action = AuditLog.ActionType.CREATE if created else AuditLog.ActionType.UPDATE

    old_values = None
    new_values = None

    if action == AuditLog.ActionType.UPDATE:
        dirty = getattr(instance, "_dirty_fields", {})
        if not dirty and not getattr(instance, "is_active", True) == False:
            return

        old_values = {k: v["old"] for k, v in dirty.items()}
        new_values = {k: v["new"] for k, v in dirty.items()}
    else:
        new_dict = model_to_dict(instance)
        new_values = {k: str(v) if v is not None else None for k, v in new_dict.items()}

    AuditLog.objects.create(
        user=user,
        action=action,
        table_name=sender._meta.verbose_name,
        record_id=str(instance.pk),
        object_name=str(instance),
        old_values=old_values,
        new_values=new_values,
        ip_address=ip,
    )


@receiver(post_delete)
def audit_log_delete(sender, instance, **kwargs):
    from apps.users.models import User

    if not (issubclass(sender, BaseModel) or sender == User):
        return

    if sender == AuditLog:
        return

    user = get_current_user()
    ip = get_current_ip()

    old_dict = model_to_dict(instance)
    old_values = {k: str(v) if v is not None else None for k, v in old_dict.items()}

    AuditLog.objects.create(
        user=user,
        action=AuditLog.ActionType.DELETE,
        table_name=sender._meta.verbose_name,
        record_id=str(instance.pk),
        object_name=str(instance),
        old_values=old_values,
        new_values=None,
        ip_address=ip,
    )
