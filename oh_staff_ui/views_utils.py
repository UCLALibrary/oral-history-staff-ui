import logging

from django.db import connection
from datetime import datetime
from lxml import etree
import requests
import uuid
from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.core.management import call_command
from django.db.models import CharField, Model, Q
from django.contrib.auth.models import User
from django.forms import BaseFormSet, Form, formset_factory
from django.http.request import HttpRequest  # for code completion
from django.utils import timezone
from oh_staff_ui.forms import (
    AltIdForm,
    AltTitleForm,
    BaseItemSequenceFormset,
    DateForm,
    DescriptionForm,
    FormatForm,
    ProjectItemForm,
    CopyrightUsageForm,
    LanguageUsageForm,
    ItemSequenceForm,
    NameUsageForm,
    PublisherUsageForm,
    ResourceUsageForm,
    SubjectUsageForm,
)
from oh_staff_ui.models import (
    AltId,
    AltTitle,
    Date,
    Description,
    Format,
    MediaFile,
    Name,
    ProjectItem,
    Subject,
    ItemCopyrightUsage,
    ItemLanguageUsage,
    ItemNameUsage,
    ItemPublisherUsage,
    ItemResourceUsage,
    ItemSubjectUsage,
)
from oh_staff_ui.classes.OralHistoryMods import OralHistoryMods

logger = logging.getLogger(__name__)


def construct_keyword_query(field: str, query: str) -> Q:
    # Always include the full query, as a single substring.
    full_q = Q(**{field + "__icontains": query})
    keywords = query.split()
    # If there's only one word, it's the same as the full query, nothing to do.
    # Otherwise, grab the first word, then AND each following word.
    if len(keywords) > 1:
        words_q = Q(**{field + "__icontains": keywords[0]})
        # All except the first word
        for word in keywords[1:]:
            words_q = words_q & Q(**{field + "__icontains": word})
        # OR the assembled set of words with the full query.
        full_q = full_q | words_q
    return full_q


def get_keyword_results(query: str) -> list:
    # look for matches in any CharField attached to any of these models
    search_models = [ProjectItem, AltId, AltTitle, Description, Name, Subject]
    search_results = []
    for model in search_models:
        model_q = Q()
        fields = [x for x in model._meta.fields if isinstance(x, CharField)]
        for field in fields:
            field_q = construct_keyword_query(field.name, query)
            model_q = model_q | field_q
        model_results = model.objects.filter(model_q)
        search_results.append(model_results)
    return search_results


def get_result_items(queryset_list: list) -> list[ProjectItem]:
    # convert list of querysets to list of ProjectItems for display
    output_projectitems = []
    # by order of search_models in get_keyword_results(),
    # queryset_list[0] contains ProjectItems
    # these are directly copied to output list
    for item in queryset_list[0]:
        output_projectitems.append(item)
    # queryset_list[1] has AltIds
    for altid in queryset_list[1]:
        output_projectitems.append(altid.item)
    # queryset_list[2] has AltTitles
    for alttitle in queryset_list[2]:
        output_projectitems.append(alttitle.item)
    # queryset_list[3] has Descriptions
    for description in queryset_list[3]:
        output_projectitems.append(description.item)
    # queryset_list[4] has Names
    for name in queryset_list[4]:
        name_usages = ItemNameUsage.objects.filter(value=name)
        for item in name_usages:
            output_projectitems.append(item.item)
    # queryset_list[5] has Subjects
    for subject in queryset_list[5]:
        subject_usages = ItemSubjectUsage.objects.filter(value=subject)
        for item in subject_usages:
            output_projectitems.append(item.item)
    # remove duplicate items
    output_projectitems_deduped = list(set(output_projectitems))
    # sort output list by title
    output_projectitems_deduped.sort(key=lambda x: x.title.lower())
    return output_projectitems_deduped


def get_search_results(
    search_type: str,
    query: str,
    item_type_filter: str,
    media_file_type_filter: str,
    status_filter: str,
) -> list[ProjectItem]:
    # Return a list of items matching the search.  Different searches have
    # different return types and sort orders; this unifies them for consistent
    # use in the view and template.

    # first, check if this is a wildcard search - if so, return all items
    # no need to check search_type
    if query == "*":
        qs_results = ProjectItem.objects.all().order_by("title")
        results_list = [item for item in qs_results]

    elif search_type == "title":
        full_query = construct_keyword_query("title", query)
        qs_results = ProjectItem.objects.filter(full_query).order_by("title")
        results_list = [item for item in qs_results]

    elif search_type == "ark":
        qs_results = ProjectItem.objects.filter(ark__icontains=query).order_by("ark")
        results_list = [item for item in qs_results]

    elif search_type == "keyword":
        search_data = get_keyword_results(query)
        # This is a sorted list of ProjectItems already, so does not need conversion to list below.
        results_list = get_result_items(search_data)

    filtered_results = filter_results_list(
        results_list, item_type_filter, media_file_type_filter, status_filter
    )
    return filtered_results


def filter_results_list(
    results_list: list[ProjectItem],
    item_type_filter: str,
    media_file_type_filter: str,
    status_filter: str,
) -> list[ProjectItem]:
    if item_type_filter != "all":
        results_list = [
            item for item in results_list if item.type.type == item_type_filter
        ]
    if media_file_type_filter != "all":
        media_files = MediaFile.objects.filter(
            file_type__file_type=media_file_type_filter
        )
        media_file_items = [media_file.item.id for media_file in media_files]
        results_list = [item for item in results_list if item.id in media_file_items]
    if status_filter != "all":
        results_list = [
            item for item in results_list if item.status.status == status_filter
        ]
    return results_list


def get_ark() -> str:
    # Real ARK minter returns simple text response which looks like this:
    # id: 21198/zz002kpxs1
    if settings.RUN_ENV == "dev":
        # Create an obviously fake, unique-ish ARK, for local development
        ark = f"FAKE/{uuid.uuid4().hex[0:10]}"
        return ark
    else:
        # Production ARKs depend on an external service, which can fail.
        try:
            response = requests.get(settings.ARK_MINTER)
            # If response.ok, no error; otherwise, raises HTTPError
            response.raise_for_status()
            ark = response.text.strip()[4:]
            return ark
        except requests.HTTPError as http_error:
            logger.error(http_error)
            # Kick it back to the calling view
            raise


def get_edit_item_context(item_id: int, user: User) -> dict:
    # Populate forms with data from database
    item = ProjectItem.objects.get(pk=item_id)
    # item_form is "bound" with this data
    item_form = ProjectItemForm(
        data={
            "parent": item.parent,
            "title": item.title,
            "type": item.type,
            "sequence": item.sequence,
            "coverage": item.coverage,
            "relation": item.relation,
            "status": item.status,
        }
    )
    alt_id_formset = get_metadata_formset(item_id, AltIdForm, AltId, "alt_ids")
    alt_title_formset = get_metadata_formset(
        item_id, AltTitleForm, AltTitle, "alt_titles"
    )
    copyright_formset = get_metadata_formset(
        item_id, CopyrightUsageForm, ItemCopyrightUsage, "copyrights"
    )
    date_formset = get_metadata_formset(item_id, DateForm, Date, "dates")
    description_formset = get_metadata_formset(
        item_id, DescriptionForm, Description, "descriptions"
    )
    format_formset = get_metadata_formset(item_id, FormatForm, Format, "formats")
    language_formset = get_metadata_formset(
        item_id, LanguageUsageForm, ItemLanguageUsage, "languages"
    )
    name_formset = get_metadata_formset(item_id, NameUsageForm, ItemNameUsage, "names")
    publisher_formset = get_metadata_formset(
        item_id, PublisherUsageForm, ItemPublisherUsage, "publishers"
    )
    resource_formset = get_metadata_formset(
        item_id, ResourceUsageForm, ItemResourceUsage, "resources"
    )
    subject_formset = get_metadata_formset(
        item_id, SubjectUsageForm, ItemSubjectUsage, "subjects"
    )
    relatives = get_relatives(item)
    # for use in the template to display delete button if needed,
    # determine if user is in the OH Staff group
    staff_status = user_in_oh_staff_group(user)
    # for use in the template to prevent deletion if item has children
    # or associated MediaFiles, get these dependencies
    children, media_files = get_item_dependencies(item)
    return {
        "item": item,
        "item_form": item_form,
        "alt_id_formset": alt_id_formset,
        "alt_title_formset": alt_title_formset,
        "copyright_formset": copyright_formset,
        "date_formset": date_formset,
        "description_formset": description_formset,
        "format_formset": format_formset,
        "language_formset": language_formset,
        "name_formset": name_formset,
        "publisher_formset": publisher_formset,
        "resource_formset": resource_formset,
        "subject_formset": subject_formset,
        "relatives": relatives,
        "public_site_url": get_public_site_url(item),
        "staff_status": staff_status,
        "children_blocking_delete": children,
        "media_files_blocking_delete": media_files,
    }


def get_public_site_url(item: ProjectItem) -> str:
    if not (
        settings.OH_PUBLIC_SITE
        and item.status.status in ("Completed", "Completed with minimal metadata")
    ):
        return None

    if item.type.type == "Series":
        return f"{settings.OH_PUBLIC_SITE}/?f[series_facet][]={item.title}"
    elif item.type.type == "Interview":
        return f"{settings.OH_PUBLIC_SITE}/catalog/{item.ark.replace('/', '-')}"
    else:
        return None


def get_metadata_formset(
    item_id: int, form: Form, model: Model, prefix: str
) -> BaseFormSet:
    """Return formset for given item and model, with initial data (if any) from database."""
    # Build list of dictionaries of initial values.
    objs = model.objects.filter(item=item_id).order_by("id")
    obj_list = []
    for obj in objs:
        # All models used here have id and value
        data_dict = {
            "usage_id": obj.id,
            "value": obj.value,
        }
        # Type is only in some of these models
        if hasattr(obj, "type"):
            data_dict["type"] = obj.type
        obj_list.append(data_dict)
    # Show empty form by default only when there's no real data already (extra=1).
    # Otherwise, show only real data (extra=0).
    extra_forms = 0 if len(obj_list) else 1
    factory = formset_factory(form, extra=extra_forms, can_delete=True)
    # formset is "unbound" with this initial data
    formset = factory(initial=obj_list, prefix=prefix)
    return formset


def save_all_item_data(item_id: int, request: HttpRequest) -> None:
    """Parse data from request and update database as appropriate."""
    # Get parent item info needed for ProjectItemForm.
    parent_item = get_parent_item(item_id)
    # Unpack data from all of the forms & formsets.
    AltIdFormset = formset_factory(AltIdForm, extra=1, can_delete=True)
    AltTitleFormset = formset_factory(AltTitleForm, extra=1, can_delete=True)
    CopyrightUsageFormset = formset_factory(
        CopyrightUsageForm, extra=1, can_delete=True
    )
    DateFormset = formset_factory(DateForm, extra=1, can_delete=True)
    DescriptionFormset = formset_factory(DescriptionForm, extra=1, can_delete=True)
    FormatFormset = formset_factory(FormatForm, extra=1, can_delete=True)
    LanguageUsageFormset = formset_factory(LanguageUsageForm, extra=1, can_delete=True)
    NameUsageFormset = formset_factory(NameUsageForm, extra=1, can_delete=True)
    PublisherUsageFormset = formset_factory(
        PublisherUsageForm, extra=1, can_delete=True
    )
    ResourceUsageFormset = formset_factory(ResourceUsageForm, extra=1, can_delete=True)
    SubjectUsageFormset = formset_factory(SubjectUsageForm, extra=1, can_delete=True)
    item_form = ProjectItemForm(request.POST, parent_item=parent_item)
    alt_id_formset = AltIdFormset(request.POST, prefix="alt_ids")
    alt_title_formset = AltTitleFormset(request.POST, prefix="alt_titles")
    copyright_formset = CopyrightUsageFormset(request.POST, prefix="copyrights")
    date_formset = DateFormset(request.POST, prefix="dates")
    description_formset = DescriptionFormset(request.POST, prefix="descriptions")
    format_formset = FormatFormset(request.POST, prefix="formats")
    language_formset = LanguageUsageFormset(request.POST, prefix="languages")
    name_formset = NameUsageFormset(request.POST, prefix="names")
    publisher_formset = PublisherUsageFormset(request.POST, prefix="publishers")
    resource_formset = ResourceUsageFormset(request.POST, prefix="resources")
    subject_formset = SubjectUsageFormset(request.POST, prefix="subjects")

    # TODO: Better way to check validity of all forms, without unpacking request twice.
    if (
        item_form.is_valid()
        & alt_id_formset.is_valid()
        & alt_title_formset.is_valid()
        & copyright_formset.is_valid()
        & date_formset.is_valid()
        & description_formset.is_valid()
        & format_formset.is_valid()
        & language_formset.is_valid()
        & name_formset.is_valid()
        & publisher_formset.is_valid()
        & resource_formset.is_valid()
        & subject_formset.is_valid()
    ):
        logger.debug(f"Saving data for item {item_id}")
        logger.debug(f"ITEM: {item_form.cleaned_data}")
        logger.debug(f"NAMES: {name_formset.cleaned_data}")
        logger.debug(f"SUBJECTS: {subject_formset.cleaned_data}")
        logger.debug(f"PUBLISHERS: {publisher_formset.cleaned_data}")
        logger.debug(f"COPYRIGHTS: {copyright_formset.cleaned_data}")
        logger.debug(f"LANGUAGES: {language_formset.cleaned_data}")
        logger.debug(f"RESOURCES: {resource_formset.cleaned_data}")
        logger.debug(f"ALT IDS: {alt_id_formset.cleaned_data}")
        logger.debug(f"ALT TITLES: {alt_title_formset.cleaned_data}")
        logger.debug(f"DESCRIPTIONS: {description_formset.cleaned_data}")
        logger.debug(f"DATES: {date_formset.cleaned_data}")
        logger.debug(f"FORMATS: {format_formset.cleaned_data}")
        # Item data
        item = ProjectItem.objects.get(pk=item_id)
        item.coverage = item_form.cleaned_data["coverage"]
        item.parent = item_form.cleaned_data["parent"]
        item.relation = item_form.cleaned_data["relation"]
        item.sequence = item_form.cleaned_data["sequence"]
        item.status = item_form.cleaned_data["status"]
        item.title = item_form.cleaned_data["title"]
        item.type = item_form.cleaned_data["type"]
        item.last_modified_date = timezone.now()
        item.last_modified_by = request.user
        item.save()
        # Other, optional, metadata types
        save_item_formset_data(item, AltId, alt_id_formset.cleaned_data)
        save_item_formset_data(item, AltTitle, alt_title_formset.cleaned_data)
        save_item_formset_data(item, Date, date_formset.cleaned_data)
        save_item_formset_data(item, Format, format_formset.cleaned_data)
        save_item_formset_data(item, Description, description_formset.cleaned_data)
        save_item_formset_data(item, ItemCopyrightUsage, copyright_formset.cleaned_data)
        save_item_formset_data(item, ItemLanguageUsage, language_formset.cleaned_data)
        save_item_formset_data(item, ItemNameUsage, name_formset.cleaned_data)
        save_item_formset_data(item, ItemPublisherUsage, publisher_formset.cleaned_data)
        save_item_formset_data(item, ItemResourceUsage, resource_formset.cleaned_data)
        save_item_formset_data(item, ItemSubjectUsage, subject_formset.cleaned_data)
        messages.success(request, "All item data has been saved.")
    else:
        # TODO: Proper handling of whatever errors can occur; for now, just debugging.
        messages.error(request, "Problem saving data!")
        logger.error(f"{item_form.errors=}")


def valid_metadata_usage(usage_data: dict) -> bool:
    # Check metadata "usage" form for valid data.

    # Reject empty dictionary from unused form.
    if not usage_data:
        return False
    # Reject unused form where user checked Delete box.
    if usage_data["usage_id"] == 0 and usage_data["DELETE"]:
        return False

    # Made it to here, form data is OK
    return True


def save_item_formset_data(item: ProjectItem, model: Model, formset_data: list) -> None:
    """Save metadata (if any) for given item and model, from given formset_data."""
    # List of dictionaries, some/all of which can be empty
    for data in formset_data:
        if valid_metadata_usage(data):
            # model = eval(model_name)
            # Populate object - all have value & item
            obj = model(value=data["value"], item=item)
            # Type is only in some of these models
            if data.get("type"):
                obj.type = data["type"]
            # Exising object with real id
            if data["usage_id"] > 0:
                obj.id = data["usage_id"]
            # Only delete if record already exists; otherwise, just don't save
            if data["DELETE"]:
                if obj.id:
                    obj.delete()
            else:
                obj.save()


def get_top_parent(item: ProjectItem) -> ProjectItem:
    current_parent = item
    while current_parent.parent:
        current_parent = current_parent.parent
    return current_parent


def get_descendants(item: ProjectItem) -> dict:
    descendants = {}
    children = ProjectItem.objects.filter(parent=item).order_by("sequence", "title")
    if not children:
        descendants = None
    else:
        for child in children:
            descendants[child] = get_descendants(child)
    return descendants


def get_relatives(item: ProjectItem) -> dict:
    top_parent = get_top_parent(item)
    partial_relatives = get_descendants(top_parent)
    relatives = {top_parent: partial_relatives}
    return relatives


def get_all_series_and_interviews() -> dict:
    # For Series browse page, get only Series and Interviews (not File items)
    # formatted as nested dicts for item_tree template.
    series_tree = {}
    all_series = ProjectItem.objects.filter(type__type="Series").order_by("title")
    for series in all_series:
        interview_tree = {}
        child_interviews = ProjectItem.objects.filter(parent=series).order_by(
            "sequence", "title"
        )
        for interview in child_interviews:
            interview_tree[interview] = None
        series_tree[series] = interview_tree
    return series_tree


def get_parent_item(item_id: int) -> ProjectItem:
    return ProjectItem.objects.get(pk=item_id).parent


def get_sequence_formset(items: list) -> BaseFormSet:
    sequence_list = []
    for item in items:
        sequence_list.append({"sequence": item.sequence})
    factory = formset_factory(
        ItemSequenceForm, extra=0, formset=BaseItemSequenceFormset, validate_min=True
    )
    # ItemSequenceForm only includes sequence field, so we need to pass items_list to formset
    # via form_kwargs in order to associate each sequence with its item.
    formset = factory(initial=sequence_list, form_kwargs={"items_list": items})
    return formset


def save_sequence_data(request: HttpRequest, items_list: list) -> None:
    factory = formset_factory(
        ItemSequenceForm, extra=0, formset=BaseItemSequenceFormset, validate_min=True
    )
    # Include items_list in form_kwargs so we can associate each sequence with its item
    formset = factory(request.POST, form_kwargs={"items_list": items_list})
    if formset.is_valid():
        for form in formset:
            if form.is_valid():
                sequence = form.cleaned_data["sequence"]
                child_item = form.item
                child_item.sequence = sequence
                child_item.last_modified_date = timezone.now()
                child_item.last_modified_by = request.user
                child_item.save()
        messages.success(request, "Sequence numbers have been saved.")
    else:
        messages.error(request, "Problem saving data!")
        logger.error(f"{formset.errors=}")


def run_process_file_command(
    item_id: int,
    file_name: str,
    file_type: str,
    request: HttpRequest,
) -> None:
    # Wrapper for Django call_command(), providing a callable
    # for running in background by thread.
    call_command(
        "process_file",
        item_id=item_id,
        file_name=file_name,
        file_type=file_type,
        request=request,
    )
    # Apparently Django starts a new db connection for each thread;
    # testing confirms this, though it does close after 30 seconds or so.
    # To be safe, explicitly close this one when done.
    connection.close()


def get_records_oai(verb: str, ark: str = None, req_url: str = None) -> str:
    # Only items with these statuses should be published via OAI.
    pi_set = ProjectItem.objects.filter(
        status__status__in=["Completed", "Completed with minimal metadata"]
    ).exclude(type__type__iexact="Series")

    if ark:
        pi_set = pi_set.filter(ark=ark)

    verb_element = etree.Element(verb)

    for pi in pi_set:
        verb_element.append(add_oai_envelope_to_mods(OralHistoryMods(pi)))

    return wrap_oai_content(verb_element, verb, ark, req_url)


def wrap_oai_content(
    xml_element: etree.Element, verb: str, ark: str, req_url: str
) -> str:
    oai_tree = get_oai_envelope()
    oai_tree.append(get_response_date_element())
    oai_tree.append(get_request_element(verb, ark, req_url))
    oai_tree.append(xml_element)

    return etree.tostring(oai_tree)


def get_oai_envelope() -> etree.Element:
    oai_envelope = """
            <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/
                http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd" />
            """
    oai_tree = etree.fromstring(oai_envelope)

    return oai_tree


def get_response_date_element() -> etree.Element:
    date_el = etree.Element("responseDate")
    date_el.text = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    return date_el


def get_request_element(
    verb: str, ark: str = None, req_url: str = None
) -> etree.Element:
    req = f"""<request metadataPrefix="mods">{req_url}</request>"""

    e_req = etree.fromstring(req)
    e_req.set("verb", verb)

    if ark:
        e_req.set("identifier", ark)

    return e_req


def get_bad_arg_error_xml(verb: str, req_url: str = None) -> str:
    """If a missing or bad argument is submitted with a request, OAI best practice is to
    return an OAI error response rather than returning a HTTP error code.

    http://www.openarchives.org/OAI/openarchivesprotocol.html#ErrorConditions

    """
    error_elem = etree.fromstring('<error code="badArgument"/>')

    return wrap_oai_error(verb, error_elem, req_url)


def get_bad_verb_error_xml(verb: str, req_url: str = None) -> str:
    """If a missing or bad verb is submitted with a request, OAI best practice is to
    return an OAI error response rather than returning a HTTP error code.

    http://www.openarchives.org/OAI/openarchivesprotocol.html#ErrorConditions

    """
    error_elem = etree.fromstring('<error code="badVerb"/>')

    return wrap_oai_error(verb, error_elem, req_url)


def wrap_oai_error(verb: str, error_elem: etree.Element, req_url: str = None) -> str:
    """OAI best practice is to return an OAI error response rather than returning a
    HTTP error code in certain cases.

    http://www.openarchives.org/OAI/openarchivesprotocol.html#ErrorConditions

    """
    oai_envelope = get_oai_envelope()

    oai_envelope.append(get_response_date_element())
    oai_envelope.append(get_request_element(verb, req_url=req_url))
    oai_envelope.append(error_elem)

    return etree.tostring(oai_envelope)


def add_oai_envelope_to_mods(ohmods: OralHistoryMods) -> etree.Element:
    record_el = etree.Element("record")
    header_el = etree.Element("header")

    id_el = etree.Element("identifier")
    id_el.text = ohmods._item.ark

    date_el = etree.Element("datestamp")
    date_el.text = ohmods._item.create_date.strftime("%Y-%m-%d")

    header_el.append(id_el)
    header_el.append(date_el)
    record_el.append(header_el)

    metadata_el = etree.Element("metadata")
    metadata_el.append(ohmods.node)
    record_el.append(metadata_el)

    return record_el


def user_in_oh_staff_group(user: User) -> bool:
    return user.groups.filter(name="Oral History Staff").exists()


def delete_file_and_children(media_file: MediaFile, user: User) -> None:
    # if file has child files, delete them first
    children = MediaFile.objects.filter(parent=media_file)
    for child in children:
        delete_file(child, user)
    # now delete the parent file
    delete_file(media_file, user)


def delete_file(media_file: MediaFile, user: User) -> None:
    # first delete file from file system
    # check for file existence with Path before attempting to delete
    file_name = media_file.file.name
    file_path = Path(settings.MEDIA_ROOT).joinpath(file_name)
    if file_path.exists():
        media_file.file.delete()
    else:
        logger.warning(
            f"File {file_name} does not exist on the file system; deleting media object anyhow."
        )
    logger.info(f"File {file_name} deleted by user {user}.")
    media_file.delete()


def delete_projectitem(project_item: ProjectItem, user: User) -> None:
    # check if item has child ProjectItems or MediaFiles, and block deletion if so
    children, media_files = get_item_dependencies(project_item)
    if children:
        logger.error(
            f"Item {project_item.title} has child items and cannot be deleted."
        )
        return
    if media_files:
        logger.error(
            f"Item {project_item.title} has associated MediaFiles and cannot be deleted."
        )
        return
    # finally, delete the item
    logger.info(f"Item {project_item.title} deleted by user {user}.")
    project_item.delete()


def get_item_dependencies(item: ProjectItem) -> tuple:
    # to check if we can delete an item, we need to check for both
    # child ProjectItems and associated MediaFiles
    children = ProjectItem.objects.filter(parent=item)
    media_files = MediaFile.objects.filter(item=item)
    return children, media_files
