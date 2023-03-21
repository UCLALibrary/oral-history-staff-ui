from django.contrib import admin
from .models import (
    ItemStatus,
    ItemType,
    ProjectItem,
    AuthoritySource,
    Language,
    Name,
    NameType,
    Subject,
    SubjectType,
    AltId,
    AltIdType,
    AltTitle,
    AltTitleType,
    Description,
    DescriptionType,
    Publisher,
    PublisherType,
    Copyright,
    CopyrightType,
    Resource,
    ResourceType,
    Format,
)


@admin.register(ItemStatus)
class ItemStatus(admin.ModelAdmin):
    list_display = ("status", "status_description")


@admin.register(ItemType)
class ItemType(admin.ModelAdmin):
    list_display = ("type", "parent")


@admin.register(ProjectItem)
class ProjectItem(admin.ModelAdmin):
    list_display = (
        "ark",
        "coverage",
        "create_date",
        "created_by",
        "last_modified_date",
        "last_modified_by",
        "parent",
        "sequence",
        "status",
        "title",
        "type",
    )


@admin.register(AuthoritySource)
class AuthoritySource(admin.ModelAdmin):
    list_display = ("source",)


@admin.register(Language)
class Language(admin.ModelAdmin):
    list_display = ("language", "source")


@admin.register(NameType)
class NameType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(Name)
class Name(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(SubjectType)
class NameType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(Subject)
class Subject(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(AltIdType)
class AltIdType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(AltId)
class AltId(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(AltTitleType)
class AltTitleType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(AltTitle)
class AltTitle(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(DescriptionType)
class DescriptionType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(Description)
class Description(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(PublisherType)
class PublisherType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(Publisher)
class Publisher(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(CopyrightType)
class CopyrightType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(Copyright)
class Copyright(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(ResourceType)
class ResourceType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(Resource)
class Resource(admin.ModelAdmin):
    list_display = ("value", "source")


@admin.register(Format)
class Format(admin.ModelAdmin):
    list_display = ("item", "value")
