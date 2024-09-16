from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class Client(models.Model):
    telegram_id = models.CharField(
        max_length=50, unique=True, verbose_name="Телеграм ID"
    )
    name = models.CharField(max_length=200, verbose_name="ФИО")
    phonenumber = PhoneNumberField(region="RU", blank=True, verbose_name="Телефон")
