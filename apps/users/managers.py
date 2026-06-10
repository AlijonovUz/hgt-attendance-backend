from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, full_name, password=None, **extra_fields):
        if not full_name:
            raise ValueError("Xodimning ism-sharifi (full_name) kiritilishi shart")
        user = self.model(full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(full_name, password, **extra_fields)

    def active(self):
        return self.filter(is_active=True, is_fired=False)

    def inactive(self):
        return self.filter(is_active=False)

    def fired(self):
        return self.filter(is_fired=True)
