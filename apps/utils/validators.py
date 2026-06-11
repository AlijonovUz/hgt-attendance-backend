import re
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

phone_validator = RegexValidator(
    regex=r"^\+998\d{9}$",
    message="Telefon raqami noto'g'ri formatda kiritildi. Kutilgan format: '+9989012345678'. Uzunligi aynan 13 ta belgi bo'lishi shart.",
)


class ComplexPasswordValidator:
    def validate(self, password, user=None):
        if not re.findall(r'[A-Z]', password):
            raise ValidationError(
                "Parol kamida bitta katta harf (A-Z) ni o'z ichiga olishi kerak.",
                code='password_no_upper',
            )
        if not re.findall(r'[a-z]', password):
            raise ValidationError(
                "Parol kamida bitta kichik harf (a-z) ni o'z ichiga olishi kerak.",
                code='password_no_lower',
            )
        if not re.findall(r'\d', password):
            raise ValidationError(
                "Parol kamida bitta raqam (0-9) ni o'z ichiga olishi kerak.",
                code='password_no_number',
            )
        if not re.findall(r'[^A-Za-z0-9]', password):
            raise ValidationError(
                "Parol kamida bitta maxsus belgi (@, #, $, %, vb.) ni o'z ichiga olishi kerak.",
                code='password_no_symbol',
            )

    def get_help_text(self):
        return "Parolingiz kamida bitta katta harf, bitta kichik harf, bitta raqam va bitta maxsus belgi saqlashi kerak."
