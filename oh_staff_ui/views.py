from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest  # for code completion
from django.http.response import HttpResponse  # for code completion
from oh_staff_ui.forms import (
    ProjectItemForm,
    ItemSearchForm,
    NameUsageFormset,
    SubjectUsageFormset,
)
from oh_staff_ui.models import ProjectItem
from oh_staff_ui.views_utils import construct_keyword_query


@login_required
def add_item(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ProjectItemForm(request.POST)
        if form.is_valid():
            # Minimal data from form;
            # most other fields set by db defaults or web service.
            # TODO: Get this from web service
            ark = "fake ark"
            # User must be logged in, so is present in request
            user = request.user
            new_item = ProjectItem(
                ark=ark,
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
    else:
        form = ProjectItemForm()
        return render(request, "oh_staff_ui/add_item.html", {"form": form})


@login_required
def edit_item(request: HttpRequest, item_id: int) -> HttpResponse:
    # TODO: Real form, and view, for editing item and its associated metadata.
    item = ProjectItem.objects.get(pk=item_id)
    if request.method == "POST":
        # item_form = ProjectItemForm(request.POST)
        pass
    else:
        # TODO: Get data via utility functions
        data = {"title": item.title, "type": item.type, "sequence": item.sequence}
        item_form = ProjectItemForm(data)
        name_formset = NameUsageFormset(prefix="names")
        subject_formset = SubjectUsageFormset(prefix="subjects")
    return render(
        request,
        "oh_staff_ui/edit_item.html",
        {
            "item": item,
            "item_form": item_form,
            "name_formset": name_formset,
            "subject_formset": subject_formset,
        },
    )


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
