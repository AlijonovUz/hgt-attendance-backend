import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from apps.utils.models import BaseModel
from apps.utils.validators import phone_validator


class Permission(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Ruxsat nomi")
    code = models.CharField(max_length=100, unique=True, verbose_name="Ruxsat kodi")

    class Meta(BaseModel.Meta):
        verbose_name = "Ruxsat (Permission)"
        verbose_name_plural = "Ruxsatlar"

    def __str__(self):
        return self.name


class Role(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Rol nomi")
    permissions = models.ManyToManyField(
        Permission, blank=True, verbose_name="Ruxsatlar"
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Rol"
        verbose_name_plural = "Rollar"

    def __str__(self):
        return self.name


class Branch(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Filial nomi")

    class Meta(BaseModel.Meta):
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"

    def __str__(self):
        return self.name


class Department(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Bo'lim nomi")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="departments",
        verbose_name="Filial",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"

    def __str__(self):
        return self.name


class Position(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Lavozim nomi")
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Bo'lim",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Lavozim"
        verbose_name_plural = "Lavozimlar"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, full_name, password=None, **extra_fields):
        if not full_name:
            raise ValueError('Xodimning ism-sharifi (full_name) kiritilishi shart')
        user = self.model(full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(full_name, password, **extra_fields)

    def active(self):
        return self.filter(is_active=True, is_fired=False)

    def inactive(self):
        return self.filter(is_active=False)

    def fired(self):
        return self.filter(is_fired=True)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(
        max_length=255, unique=True, verbose_name="F.I.Sh"
    )
    jshshir = models.CharField(
        max_length=14, unique=True, null=True, blank=True, verbose_name="JShShIR"
    )
    phone = models.CharField(
        max_length=13, 
        unique=True, 
        null=True, 
        blank=True, 
        validators=[phone_validator],
        verbose_name="Telefon"
    )
    face_image = models.ImageField(
        upload_to="faces/", null=True, blank=True, verbose_name="Face ID rasm"
    )

    is_fired = models.BooleanField(default=False)

    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Filial",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Bo'lim",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Lavozim",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Rol",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    username = None
    USERNAME_FIELD = "full_name"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ["-created_at"]

    def has_permission(self, perm_code):
        if self.is_superuser:
            return True

        if self.role:
            return self.role.permissions.filter(code=perm_code).exists()
        return False

    def has_any_permission(self, perm_codes):
        if self.is_superuser:
            return True
            
        if self.role:
            return self.role.permissions.filter(code__in=perm_codes).exists()
        return False

    def __str__(self):
        return self.full_name
