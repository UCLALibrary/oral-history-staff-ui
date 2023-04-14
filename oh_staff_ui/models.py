from django.db import models
from django.conf import settings
from django.utils import timezone


class ItemStatus(models.Model):
    status = models.CharField(max_length=40)
    status_description = models.CharField(max_length=256)

    def __str__(self):
        return self.status

    class Meta:
        verbose_name_plural = "Item statuses"
        indexes = [
            models.Index(fields=["status"]),
        ]


def get_default_status():
    # Provides default value for new ProjectItem status field.
    # Caution: Must be updated if this literal value changes.
    return ItemStatus.objects.get(status="In progress").id


class ItemType(models.Model):
    type = models.CharField(max_length=40)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


def get_default_type():
    # Provides default value for new ProjectItem type field.
    # Caution: Must be updated if this literal value changes.
    return ItemType.objects.get(type="Audio").id


class ProjectItem(models.Model):
    ark = models.CharField(max_length=40, blank=False, null=False)
    coverage = models.CharField(max_length=256, blank=True, null=True)
    create_date = models.DateField(blank=False, null=False, default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        related_name="+",
    )
    last_modified_date = models.DateField(blank=False, null=False, default=timezone.now)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        related_name="+",
    )
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    relation = models.CharField(max_length=256, blank=True, null=True)
    sequence = models.IntegerField(blank=False, null=False, default=0)
    status = models.ForeignKey(
        ItemStatus,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        default=get_default_status,
    )
    title = models.CharField(max_length=256, blank=False, null=False)
    type = models.ForeignKey(
        ItemType, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=["ark"]),
            models.Index(fields=["title"]),
        ]


class AuthoritySource(models.Model):
    source = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.source

    class Meta:
        indexes = [
            models.Index(fields=["source"]),
        ]


class Language(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value


class ItemLanguageUsage(models.Model):
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    value = models.ForeignKey(
        Language, on_delete=models.PROTECT, blank=False, null=False
    )


class NameType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class Name(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return f"{self.value} ({self.source})"

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class ItemNameUsage(models.Model):
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    value = models.ForeignKey(Name, on_delete=models.PROTECT, blank=False, null=False)
    type = models.ForeignKey(
        NameType, on_delete=models.PROTECT, blank=False, null=False
    )


class SubjectType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class Subject(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class ItemSubjectUsage(models.Model):
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    value = models.ForeignKey(
        Subject, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        SubjectType, on_delete=models.PROTECT, blank=False, null=False
    )


class AltTitleType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class AltTitle(models.Model):
    value = models.CharField(max_length=512, blank=False, null=False)
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        AltTitleType, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class AltIdType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class AltId(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        AltIdType, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class DescriptionType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class Description(models.Model):
    value = models.CharField(max_length=8000, blank=False, null=False)
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        DescriptionType, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value


class PublisherType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class Publisher(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class ItemPublisherUsage(models.Model):
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    value = models.ForeignKey(
        Publisher, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        PublisherType, on_delete=models.PROTECT, blank=False, null=False
    )


class CopyrightType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class Copyright(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class ItemCopyrightUsage(models.Model):
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    value = models.ForeignKey(
        Copyright, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        CopyrightType, on_delete=models.PROTECT, blank=False, null=False
    )


class ResourceType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class Resource(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    source = models.ForeignKey(
        AuthoritySource, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class ItemResourceUsage(models.Model):
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    value = models.ForeignKey(
        Resource, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        ResourceType, on_delete=models.PROTECT, blank=False, null=False
    )


class Format(models.Model):
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    value = models.CharField(max_length=1024, blank=False, null=False)

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class DateType(models.Model):
    type = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.type

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
        ]


class Date(models.Model):
    value = models.CharField(max_length=256, blank=False, null=False)
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
    type = models.ForeignKey(
        DateType, on_delete=models.PROTECT, blank=False, null=False
    )

    def __str__(self):
        return self.value

    class Meta:
        indexes = [
            models.Index(fields=["value"]),
        ]


class MediaFileType(models.Model):
    file_type = models.CharField(max_length=40, blank=False, null=False)
    file_type_description = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.file_type

    class Meta:
        indexes = [
            models.Index(fields=["file_type"]),
        ]
        ordering = ["file_type"]


def get_file_directory(instance, filename):
    # Eventually this will determine where a MediaFile.file should be stored.
    # For now, use constant samples subdirectory
    # and ignore instance parameter passed in by FileField.
    return f"samples/managed/{filename}"


class MediaFile(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        related_name="+",
    )
    create_date = models.DateField(blank=False, null=False, default=timezone.now)
    # TODO: Correct value for upload_to, relative to MEDIA_ROOT
    file = models.FileField(upload_to=get_file_directory)
    file_type = models.ForeignKey(
        MediaFileType, on_delete=models.PROTECT, blank=False, null=False
    )
    sequence = models.IntegerField(blank=False, null=False, default=0)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
