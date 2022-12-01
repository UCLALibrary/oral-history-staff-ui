from django.contrib import admin
from .models import ItemStatus


@admin.register(ItemStatus)
class ItemStatus(admin.ModelAdmin):
    list_display = ("status", "status_description")
