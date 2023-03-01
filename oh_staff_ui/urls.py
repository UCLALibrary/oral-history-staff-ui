from django.urls import path
from . import views

urlpatterns = [
    path("add_item/", views.add_item),
    path("", views.add_item),  # TODO: Change this to something better.....
]
