from django.contrib import admin
from .models import (
    ItemStatus,
    ItemType,
    AuthoritySource,
    Language,
    Name,
    NameType,
    Subject,
    SubjectType,
    AltIdType,
    AltTitleType,
    DescriptionType,
    Publisher,
    PublisherType,
    Copyright,
    CopyrightType,
    Resource,
    ResourceType,
    DateType,
    MediaFileType,
)


@admin.register(ItemStatus)
class ItemStatus(admin.ModelAdmin):
    list_display = ("status", "status_description")
    ordering = ("status", "status_description")


@admin.register(ItemType)
class ItemType(admin.ModelAdmin):
    list_display = ("type", "parent")
    ordering = ("type", "parent")


@admin.register(AuthoritySource)
class AuthoritySource(admin.ModelAdmin):
    list_display = ("source",)
    ordering = ("source",)


@admin.register(Language)
class Language(admin.ModelAdmin):
    list_display = ("value", "source")
    ordering = ("value", "source")


@admin.register(NameType)
class NameType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(Name)
class Name(admin.ModelAdmin):
    list_display = ("value", "source")
    ordering = ("value", "source")
    search_fields = ("value",)
    list_filter = ("source",)


@admin.register(SubjectType)
class NameType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(Subject)
class Subject(admin.ModelAdmin):
    list_display = ("value", "source")
    ordering = ("value", "source")
    search_fields = ("value",)
    list_filter = ("source",)


@admin.register(AltIdType)
class AltIdType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(AltTitleType)
class AltTitleType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(DescriptionType)
class DescriptionType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(PublisherType)
class PublisherType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(Publisher)
class Publisher(admin.ModelAdmin):
    list_display = ("value", "source")
    ordering = ("value", "source")


@admin.register(CopyrightType)
class CopyrightType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(Copyright)
class Copyright(admin.ModelAdmin):
    list_display = ("value", "source")
    ordering = ("value", "source")


@admin.register(ResourceType)
class ResourceType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(Resource)
class Resource(admin.ModelAdmin):
    list_display = ("value", "source")
    ordering = ("value", "source")


@admin.register(DateType)
class DateType(admin.ModelAdmin):
    list_display = ("type",)
    ordering = ("type",)


@admin.register(MediaFileType)
class MediaFileType(admin.ModelAdmin):
    list_display = ("file_type", "file_type_description")
    ordering = ("file_type", "file_type_description")
