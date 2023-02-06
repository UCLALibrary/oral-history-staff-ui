from django.contrib import admin
from .models import ItemStatus, ItemType, ProjectItem, AuthoritySource, Language


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
