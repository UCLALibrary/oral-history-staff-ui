from django.db import models

# Create your models here.


class ItemStatus(models.Model):
    status = models.CharField(max_length=40)
    status_description = models.CharField(max_length=256)

    class Meta:
        verbose_name_plural = "Item statuses"
