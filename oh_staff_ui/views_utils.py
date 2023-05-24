import logging
from django.db import connection
import requests
import uuid
from django.conf import settings
from django.contrib import messages
from django.core.management import call_command
from django.db.models import Q, Model, CharField
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


def get_result_items(queryset_list: list) -> list:
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
            logger.fatal(http_error)
            # Kick it back to the calling view
            raise


def get_edit_item_context(item_id: int) -> dict:
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
    }


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
        logger.info(f"Saving data for item {item_id}")
        logger.info(f"ITEM: {item_form.cleaned_data}")
        logger.info(f"NAMES: {name_formset.cleaned_data}")
        logger.info(f"SUBJECTS: {subject_formset.cleaned_data}")
        logger.info(f"PUBLISHERS: {publisher_formset.cleaned_data}")
        logger.info(f"COPYRIGHTS: {copyright_formset.cleaned_data}")
        logger.info(f"LANGUAGES: {language_formset.cleaned_data}")
        logger.info(f"RESOURCES: {resource_formset.cleaned_data}")
        logger.info(f"ALT IDS: {alt_id_formset.cleaned_data}")
        logger.info(f"ALT TITLES: {alt_title_formset.cleaned_data}")
        logger.info(f"DESCRIPTIONS: {description_formset.cleaned_data}")
        logger.info(f"DATES: {date_formset.cleaned_data}")
        logger.info(f"FORMATS: {format_formset.cleaned_data}")
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
