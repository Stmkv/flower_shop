from django.contrib import admin

from tg_bot.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "name", "phonenumber")
