from django.db import models


class Bouquet(models.Model):
    event_type = models.CharField(
        max_length=255
    )  # Тип события (день рождения, свадьба и т.д.)
    price_range = models.CharField(max_length=255)  # Диапазон цен (~500, ~1000 и т.д.)
    photo = models.ImageField(upload_to="bouquet_photos/")  # Путь к фото букета
    description = models.TextField()  # Описание букета
    composition = models.TextField()  # Цветочный состав
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Стоимость букета

    def __str__(self):
        return f"{self.event_type} - {self.price_range}"


class Order(models.Model):
    user_id = models.IntegerField()
    bouquet = models.ForeignKey(Bouquet, on_delete=models.CASCADE)
    date_ordered = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, default="Pending")

    name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)
    delivery_time = models.TimeField(blank=True, null=True)  # Статус заказа

    def __str__(self):
        return f"Order {self.id} by User {self.user_id}"
