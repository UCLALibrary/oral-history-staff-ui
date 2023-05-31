from pathlib import Path
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


class ProjectItem(models.Model):
    ark = models.CharField(max_length=40, blank=False, null=False)
    coverage = models.CharField(max_length=256, blank=True, null=False, default="")
    create_date = models.DateTimeField(blank=False, null=False, default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        related_name="+",
    )
    last_modified_date = models.DateTimeField(
        blank=False, null=False, default=timezone.now
    )
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        related_name="+",
    )
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    relation = models.CharField(max_length=256, blank=True, null=False, default="")
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "value"], name="language_value_unique"
            )
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "value", "type"], name="name_value_type_unique"
            )
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "value", "type"], name="subject_value_type_unique"
            )
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "value", "type"], name="publisher_value_type_unique"
            )
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "value", "type"], name="copyright_value_type_unique"
            )
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "value", "type"], name="resource_value_type_unique"
            )
        ]


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
    # TODO: Change file_code null=False after successful migration / data load.
    file_code = models.CharField(max_length=40, blank=False, null=True, unique=True)
    file_type = models.CharField(max_length=40, blank=False, null=False, unique=True)
    file_type_description = models.CharField(max_length=256, blank=False, null=False)

    def __str__(self):
        return self.file_type

    class Meta:
        ordering = ["file_type"]


class MediaFile(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        related_name="+",
    )
    create_date = models.DateTimeField(blank=False, null=False, default=timezone.now)
    file = models.FileField()
    # Files, especially masters, may not always be accessible to this application after creation,
    # so we can't rely on getting file size from FileField; capture size on creation.
    file_size = models.PositiveBigIntegerField(null=False, default=0)
    file_type = models.ForeignKey(
        MediaFileType, on_delete=models.PROTECT, blank=False, null=False
    )
    original_file_name = models.CharField(max_length=256, blank=False, null=False)
    # TODO: Change this: remove blank, change default to 1?
    sequence = models.IntegerField(blank=False, null=False, default=0)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )

    def save(self, *args, **kwargs):
        # When files are deleted, self.file.name is already None at this point.
        if self.file.name is not None:
            new_name = self.file.name
            # Throw an exception if file itself exists, or if there's an object for it already.
            # Check both, since masters could be moved out of local filesystem after a while.
            if Path(new_name).exists() or MediaFile.objects.filter(file=new_name):
                raise FileExistsError(f"File already exists: {new_name}")
        super().save(*args, **kwargs)

    @property
    def file_name_only(self) -> str:
        # Convenience method which returns just the file name, not including the full path.
        # Used for display in templates.
        return Path(self.file.name).name

    @property
    def file_url(self) -> str:
        # Calculate URL for a file, based on its path.  URLs are *not* stored in the database.
        # Only meaningful for production files, not in development environment.

        # Skip masters for now, until policy is resolved.
        file_name = self.file.name
        if "/masters/" in file_name:
            file_url = ""
        # Non-audio submasters & thumbnails
        elif file_name.startswith("oh_static/"):
            file_url = file_name.replace(
                "oh_static/", "https://static.library.ucla.edu/oralhistory/"
            )
        # Audio submasters
        elif file_name.startswith("oh_wowza/"):
            file_url = file_name.replace(
                "oh_wowza/",
                "https://wowza.library.ucla.edu/dlp/definst/mp3:oralhistory/",
            )
            file_url += "/playlist.m3u8"
        else:
            file_url = ""
        return file_url


class MediaFileError(models.Model):
    """Error messages related to MediaFile processing.

    MediaFile records may not exist, if error happens during creation of them,
    so this links to the ProjectItem record being used.
    """

    create_date = models.DateTimeField(blank=False, null=False, default=timezone.now)
    file_name = models.CharField(max_length=256, blank=False, null=False)
    # message can contain large stack traces.
    message = models.TextField(blank=False, null=False)
    item = models.ForeignKey(
        ProjectItem, on_delete=models.PROTECT, blank=False, null=False
    )
