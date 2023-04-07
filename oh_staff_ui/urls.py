from django.urls import path
from . import views

urlpatterns = [
    path("add_item/", views.add_item, name="add_item"),
    path("add_item/<int:parent_id>", views.add_item, name="add_item_from_parent"),
    path("item/<int:item_id>", views.edit_item, name="edit_item"),
    path("", views.add_item),  # TODO: Change this to something better.....
    path("item_search/", views.item_search, name="item_search"),
    path(
        "search_results/<str:search_type>/<path:query>",
        views.search_results,
        name="search_results",
    ),
]
