from django.urls import path
from . import views

urlpatterns = [
    path("add_item/", views.add_item, name="add_item"),
    path("item/<int:item_id>", views.edit_item, name="edit_item"),
    path("", views.add_item),  # TODO: Change this to something better.....
]
