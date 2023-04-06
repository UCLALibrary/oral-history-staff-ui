import logging
from requests.exceptions import HTTPError
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest  # for code completion
from django.http.response import HttpResponse  # for code completion
from oh_staff_ui.forms import (
    ProjectItemForm,
    ItemSearchForm,
)
from oh_staff_ui.models import ProjectItem
from oh_staff_ui.views_utils import (
    construct_keyword_query,
    get_ark,
    get_edit_item_context,
    save_all_item_data,
)

logger = logging.getLogger(__name__)


@login_required
def add_item(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ProjectItemForm(request.POST)
        if form.is_valid():
            # Minimal data from form;
            # most other fields set by db defaults or web service.

            # Production ARKs depend on an external service, which can fail.
            try:
                ark = get_ark()
                # User must be logged in, so is present in request
                user = request.user
                new_item = ProjectItem(
                    ark=ark,
                    parent=form.cleaned_data["parent"],
                    sequence=form.cleaned_data["sequence"],
                    title=form.cleaned_data["title"],
                    type=form.cleaned_data["type"],
                    created_by=user,
                    last_modified_by=user,
                )
                new_item.save()
                # Pass newly created item to edit form
                item_id = new_item.pk
                return redirect("edit_item", item_id=item_id)
            except HTTPError:
                custom_errors = [
                    "The ARK minter was unable to provide an ARK. Your record was not saved."
                ]
                return render(
                    request,
                    "oh_staff_ui/add_item.html",
                    {"form": form, "custom_errors": custom_errors},
                )
    else:
        form = ProjectItemForm()
        return render(request, "oh_staff_ui/add_item.html", {"form": form})


@login_required
def edit_item(request: HttpRequest, item_id: int) -> HttpResponse:
    logger.info("\n==========================================")
    if request.method == "POST":
        save_all_item_data(item_id, request)
    context = get_edit_item_context(item_id)
    return render(request, "oh_staff_ui/edit_item.html", context)


@login_required
def item_search(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ItemSearchForm(request.POST)
        if form.is_valid():
            return redirect(
                "search_results",
                search_type=form.cleaned_data["search_type"],
                query=form.cleaned_data["query"],
            )
    else:
        form = ItemSearchForm()
        return render(request, "oh_staff_ui/item_search.html", {"form": form})


@login_required
def search_results(request: HttpRequest, search_type: str, query: str) -> HttpResponse:
    if search_type == "title":
        full_query = construct_keyword_query(query)
        results = ProjectItem.objects.filter(full_query).order_by("title").values()
    elif search_type == "ark":
        results = (
            ProjectItem.objects.filter(ark__icontains=query).order_by("ark").values()
        )
    return render(request, "oh_staff_ui/search_results.html", {"results": results})
