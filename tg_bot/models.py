from django.db import models


class Event(models.Model):
    user_id = models.IntegerField()
    event_type = models.CharField(max_length=255)
    custom_event = models.CharField(max_length=255, blank=True, null=True)
    price = models.CharField(max_length=255, blank=True, null=True)
