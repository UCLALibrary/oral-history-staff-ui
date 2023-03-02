from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from oh_staff_ui.forms import ProjectItemForm
from oh_staff_ui.models import ProjectItem


@login_required
def add_item(request):
    if request.method == "POST":
        form = ProjectItemForm(request.POST)
        if form.is_valid():
            # Minimal data from form;
            # most other fields set by db defaults or web service.
            # sequence = form.cleaned_data["sequence"]
            # title = form.cleaned_data["title"]
            # TODO: Get this from web service
            ark = "fake ark"
            # TODO: Get real user info
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
    else:
        form = ProjectItemForm()
    return render(request, "oh_staff_ui/add_item.html", {"form": form})
