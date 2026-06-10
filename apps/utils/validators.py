from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+998\d{9}$",
    message="Telefon raqami noto'g'ri formatda kiritildi. Kutilgan format: '+9989012345678'. Uzunligi aynan 13 ta belgi bo'lishi shart.",
)
