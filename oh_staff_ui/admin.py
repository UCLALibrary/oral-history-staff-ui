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
    list_display = ("value", "type", "source")


@admin.register(SubjectType)
class NameType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(Subject)
class Subject(admin.ModelAdmin):
    list_display = ("value", "type", "source")


@admin.register(AltIdType)
class NameType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(AltId)
class Subject(admin.ModelAdmin):
    list_display = ("value", "type", "source")


@admin.register(AltTitleType)
class NameType(admin.ModelAdmin):
    list_display = ("type",)


@admin.register(AltTitle)
class Subject(admin.ModelAdmin):
    list_display = ("value", "type", "source")
