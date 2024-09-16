from django.contrib import admin

from tg_bot.models import Bouquet, Order


@admin.register(Bouquet)
class BouquetAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "price_range",
        "photo",
        "description",
        "composition",
        "price",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "bouquet",
        "date_ordered",
        "status",
    )
