from django.db import models
from django.conf import settings

# Create your models here.


class ItemStatus(models.Model):
    status = models.CharField(max_length=40)
    status_description = models.CharField(max_length=256)

    def __str__(self):
        return self.status

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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
    )
    last_modified_date = models.DateField()
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
    )
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    sequence = models.IntegerField(blank=False, null=False, default=1)
    status = models.ForeignKey(
        ItemStatus, on_delete=models.SET_NULL, blank=True, null=True
    )
    title = models.CharField(max_length=256, blank=False, null=False)
    type = models.ForeignKey(ItemType, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.title


class AuthoritySource(models.Model):
    source = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.source


class Language(models.Model):
    language = models.CharField(max_length=256, blank=False, null=False)
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.CASCADE, blank=False, null=False
    )

    def __str__(self):
        return self.language


class NameType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type


class Name(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    type = models.ForeignKey(
        NameType, on_delete=models.CASCADE, blank=False, null=False
    )
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.CASCADE, blank=False, null=False
    )

    def __str__(self):
        return self.value
