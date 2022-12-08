from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class ItemStatus(models.Model):
    status = models.CharField(max_length=40)
    status_description = models.CharField(max_length=256)

    class Meta:
        verbose_name_plural = "Item statuses"


class ItemType(models.Model):
    type = models.CharField(max_length=40)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.type


class ProjectItem(models.Model):

    ark = models.CharField(max_length=40, blank=False, null=False)
    create_date = models.DateField()
    created_by = models.ForeignKey(User)
    last_edit_date = models.DateField()
    last_modified_by = models.ForeignKey(User)
    parent = models.ForeignKey("self")
    sequence = models.IntegerField()
    status = models.ForeignKey(ItemStatus, blank=True, null=True)
    title = models.CharField(max_length=256, blank=False, null=False)
    type = models.ForeignKey(ItemType, blank=True, null=True)

    def __str__(self):
        return self.title
