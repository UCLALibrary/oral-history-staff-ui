import logging
from threading import Thread
from requests.exceptions import HTTPError
from django.contrib import messages
from django.core.management.base import CommandError
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest  # for code completion
from django.http.response import HttpResponse  # for code completion
from django.http.response import HttpResponseBadRequest
from oh_staff_ui.forms import (
    FileUploadForm,
    ProjectItemForm,
    ItemSearchForm,
)
from oh_staff_ui.models import MediaFile, MediaFileError, ProjectItem
from oh_staff_ui.views_utils import (
    get_ark,
    get_edit_item_context,
    get_all_series_and_interviews,
    get_search_results,
    get_sequence_formset,
    run_process_file_command,
    save_all_item_data,
    save_sequence_data,
    get_listrecords_oai,
    get_record_oai,
)

logger = logging.getLogger(__name__)


@login_required
def add_item(request: HttpRequest, parent_id: int | None = None) -> HttpResponse:
    # Get parent_item for later use.
    parent_item: ProjectItem = None
    if parent_id:
        parent_item = ProjectItem.objects.get(pk=parent_id)

    if request.method == "POST":
        form = ProjectItemForm(request.POST, parent_item=parent_item)
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
        if parent_id:
            # TODO: Consider further changes to form to make "initial" unneeded here.
            form = ProjectItemForm(
                initial={"parent": parent_item}, parent_item=parent_item
            )
        else:
            form = ProjectItemForm(parent_item=parent_item)
    return render(request, "oh_staff_ui/add_item.html", {"form": form})


@login_required
def edit_item(request: HttpRequest, item_id: int) -> HttpResponse:
    if request.method == "POST":
        save_all_item_data(item_id, request)
    context = get_edit_item_context(item_id)
    return render(request, "oh_staff_ui/edit_item.html", context)


@login_required
def item_search(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ItemSearchForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["search_type"] == "status":
                typed_query = form.cleaned_data["status_query"]
            else:
                typed_query = form.cleaned_data["char_query"]
            return redirect(
                "search_results",
                search_type=form.cleaned_data["search_type"],
                query=typed_query,
            )
    else:
        form = ItemSearchForm()
        return render(request, "oh_staff_ui/item_search.html", {"form": form})


@login_required
def search_results(request: HttpRequest, search_type: str, query: str) -> HttpResponse:
    results = get_search_results(search_type, query)
    return render(request, "oh_staff_ui/search_results.html", {"results": results})


@login_required
def show_log(request, line_count: int = 200) -> HttpResponse:
    log_file = "logs/application.log"
    try:
        with open(log_file, "r") as f:
            # Get just the last line_count lines in the log.
            lines = f.readlines()[-line_count:]
            # Template prints these as a single block, so join lines into one chunk.
            log_data = "".join(lines)
    except FileNotFoundError:
        log_data = f"Log file {log_file} not found"

    return render(request, "oh_staff_ui/log.html", {"log_data": log_data})


@login_required
def upload_file(request: HttpRequest, item_id: int) -> HttpResponse:
    item = ProjectItem.objects.get(pk=item_id)
    files = MediaFile.objects.filter(item=item)
    file_errors = MediaFileError.objects.filter(item=item).order_by("create_date")
    if request.method == "POST":
        # Pass item_id and request to submitted form to help with validation.
        form = FileUploadForm(request.POST, item_id=item_id, request=request)
        if form.is_valid():
            file_type = form.cleaned_data["file_type"]
            file_name = form.cleaned_data["file_name"]
            # Audio masters are usually large; process in background.
            if file_type.file_code == "audio_master":
                messages.info(
                    request,
                    f"{file_name} is being processed in the background. "
                    "You can continue editing while this is happening.",
                )
                thread = Thread(
                    target=run_process_file_command,
                    args=[item_id, file_name, file_type, request],
                    daemon=True,
                )
                thread.start()
            else:
                try:
                    run_process_file_command(
                        item_id=item_id,
                        file_name=file_name,
                        file_type=file_type,
                        request=request,
                    )
                    messages.success(request, f"{file_name} was successfully processed")
                # Errors from process_file, called above
                except (CommandError, FileExistsError, ValueError) as e:
                    messages.error(request, str(e))
                except Exception as e:
                    logger.exception(e)
                    messages.error(request, "General error: " + str(e))
            # Redirect (via GET) so user refreshing page does not resubmit form.
            return redirect("upload_file", item_id=item_id)
    else:
        form = FileUploadForm()
    context = {"item": item, "files": files, "file_errors": file_errors, "form": form}
    return render(request, "oh_staff_ui/upload_file.html", context)


@login_required
def order_files(request: HttpRequest, item_id: int) -> HttpResponse:
    item = ProjectItem.objects.get(pk=item_id)
    children = list(
        ProjectItem.objects.filter(parent=item).order_by("sequence", "title")
    )
    if request.method == "POST":
        save_sequence_data(request, children)
        # Redirect (via GET) so user refreshing page does not resubmit form.
        return redirect("order_files", item_id=item_id)
    formset = get_sequence_formset(children)
    context = {"item": item, "formset": formset}
    return render(request, "oh_staff_ui/order_files.html", context)


@login_required
def browse(request: HttpRequest) -> HttpResponse:
    context = {"relatives": get_all_series_and_interviews()}
    return render(request, "oh_staff_ui/browse.html", context)


def oai(request: HttpRequest) -> HttpResponse:
    try:
        # Verb is required, ark is optional
        verb = request.GET["verb"]
        ark = request.GET.get("identifier")

        if verb not in ("GetRecord", "ListRecords"):
            raise Exception

        if verb == "GetRecord":
            xml_content = get_record_oai(ark)

        elif verb == "ListRecords":
            xml_content = get_listrecords_oai("ListRecords")

        return HttpResponse(xml_content, content_type="text/xml")

    except Exception as e:
        return HttpResponseBadRequest()
