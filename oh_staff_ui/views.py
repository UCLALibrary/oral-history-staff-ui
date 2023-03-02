from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest  # for code completion
from django.http.response import HttpResponse  # for code completion
from oh_staff_ui.forms import ProjectItemForm
from oh_staff_ui.models import ProjectItem


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
    return render(request, "oh_staff_ui/edit_item.html", {"item": item})
