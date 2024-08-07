from django.urls import path, re_path
from . import views

urlpatterns = [
    path("add_item/", views.add_item, name="add_item"),
    path("add_item/<int:parent_id>", views.add_item, name="add_item_from_parent"),
    path("item/<int:item_id>", views.edit_item, name="edit_item"),
    path("delete_item/<int:item_id>", views.delete_item, name="delete_item"),
    path("", views.item_search),
    path("item_search/", views.item_search, name="item_search"),
    path(
        "search_results/<str:search_type>/<str:status_filter>/"
        "<str:media_file_type_filter>/<str:item_type_filter>/<path:query>",
        views.search_results,
        name="search_results",
    ),
    path("logs/", views.show_log, name="show_log"),
    path("logs/<int:line_count>", views.show_log, name="show_log"),
    path("upload_file/<int:item_id>", views.upload_file, name="upload_file"),
    path("delete_file/<int:file_id>", views.delete_file, name="delete_file"),
    path("order_files/<int:item_id>", views.order_files, name="order_files"),
    path("browse/", views.browse, name="browse"),
    # Allow staff access to download media files
    re_path(r"^media/(?P<path>.*)$", views.serve_media_file, name="serve_media_file"),
    # To follow OAI practice, a query parameter combination is requred of either:
    # verb=GetRecord and identifier={ark_value}
    # verb=ListRecords
    path("oai/", views.oai, name="oai"),
    path("release_notes/", views.release_notes, name="release_notes"),
]
