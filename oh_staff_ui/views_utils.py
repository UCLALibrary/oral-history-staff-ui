import logging
import requests
import uuid
from django.conf import settings
from django.db.models import Q
from django.forms import BaseFormSet, formset_factory
from django.http.request import HttpRequest  # for code completion
from django.utils import timezone
from oh_staff_ui.forms import (
    ProjectItemForm,
    CopyrightUsageForm,
    LanguageUsageForm,
    NameUsageForm,
    PublisherUsageForm,
    ResourceUsageForm,
    SubjectUsageForm,
)
from oh_staff_ui.models import (
    ProjectItem,
    ItemCopyrightUsage,
    ItemLanguageUsage,
    ItemNameUsage,
    ItemPublisherUsage,
    ItemResourceUsage,
    ItemSubjectUsage,
)

logger = logging.getLogger(__name__)


def construct_keyword_query(query: str) -> Q:
    # Always include the full query, as a single substring.
    full_q = Q(title__icontains=query)
    keywords = query.split()
    # If there's only one word, it's the same as the full query, nothing to do.
    # Otherwise, grab the first word, then AND each following word.
    if len(keywords) > 1:
        words_q = Q(title__icontains=keywords[0])
        # All except the first word
        for word in keywords[1:]:
            words_q = words_q & Q(title__icontains=word)
        # OR the assembled set of words with the full query.
        full_q = full_q | words_q
    return full_q


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
            "title": item.title,
            "type": item.type,
            "sequence": item.sequence,
            "coverage": item.coverage,
            "status": item.status,
        }
    )
    name_formset = get_name_formset(item_id)
    subject_formset = get_subject_formset(item_id)
    publisher_formset = get_publisher_formset(item_id)
    copyright_formset = get_copyright_formset(item_id)
    language_formset = get_language_formset(item_id)
    resource_formset = get_resource_formset(item_id)
    return {
        "item": item,
        "item_form": item_form,
        "copyright_formset": copyright_formset,
        "language_formset": language_formset,
        "name_formset": name_formset,
        "publisher_formset": publisher_formset,
        "resource_formset": resource_formset,
        "subject_formset": subject_formset,
    }


def get_copyright_formset(item_id: int) -> BaseFormSet:
    CopyrightUsageFormset = formset_factory(
        CopyrightUsageForm, extra=1, can_delete=True
    )
    # Build list of dictionaries of initial values.
    copyrights = ItemCopyrightUsage.objects.filter(item=item_id).order_by("id")
    copyright_list = []
    for copyright in copyrights:
        copyright_list.append(
            {
                "usage_id": copyright.id,
                "type": copyright.type,
                "copyright": copyright.copyright,
            }
        )
    # copyright_formset is "unbound" with this initial data
    copyright_formset = CopyrightUsageFormset(
        initial=copyright_list, prefix="copyrights"
    )
    return copyright_formset


def get_language_formset(item_id: int) -> BaseFormSet:
    LanguageUsageFormset = formset_factory(LanguageUsageForm, extra=1, can_delete=True)
    # Build list of dictionaries of initial values.
    languages = ItemLanguageUsage.objects.filter(item=item_id).order_by("id")
    language_list = []
    for language in languages:
        language_list.append(
            {
                "usage_id": language.id,
                "language": language.language,
            }
        )
    # language_formset is "unbound" with this initial data
    language_formset = LanguageUsageFormset(initial=language_list, prefix="languages")
    return language_formset


def get_name_formset(item_id: int) -> BaseFormSet:
    NameUsageFormset = formset_factory(NameUsageForm, extra=1, can_delete=True)
    # Build list of dictionaries of initial values.
    names = ItemNameUsage.objects.filter(item=item_id).order_by("id")
    name_list = []
    for name in names:
        name_list.append(
            {
                "usage_id": name.id,
                "type": name.type,
                "name": name.name,
            }
        )
    # name_formset is "unbound" with this initial data
    name_formset = NameUsageFormset(initial=name_list, prefix="names")
    return name_formset


def get_publisher_formset(item_id: int) -> BaseFormSet:
    PublisherUsageFormset = formset_factory(
        PublisherUsageForm, extra=1, can_delete=True
    )
    # Build list of dictionaries of initial values.
    publishers = ItemPublisherUsage.objects.filter(item=item_id).order_by("id")
    publisher_list = []
    for publisher in publishers:
        publisher_list.append(
            {
                "usage_id": publisher.id,
                "type": publisher.type,
                "publisher": publisher.publisher,
            }
        )
    # publisher_formset is "unbound" with this initial data
    publisher_formset = PublisherUsageFormset(
        initial=publisher_list, prefix="publishers"
    )
    return publisher_formset


def get_resource_formset(item_id: int) -> BaseFormSet:
    ResourceUsageFormset = formset_factory(ResourceUsageForm, extra=1, can_delete=True)
    # Build list of dictionaries of initial values.
    resources = ItemResourceUsage.objects.filter(item=item_id).order_by("id")
    resource_list = []
    for resource in resources:
        resource_list.append(
            {
                "usage_id": resource.id,
                "type": resource.type,
                "resource": resource.resource,
            }
        )
    # resource_formset is "unbound" with this initial data
    resource_formset = ResourceUsageFormset(initial=resource_list, prefix="resources")
    return resource_formset


def get_subject_formset(item_id: int) -> BaseFormSet:
    SubjectUsageFormset = formset_factory(SubjectUsageForm, extra=1, can_delete=True)
    # Build list of dictionaries of initial values.
    subjects = ItemSubjectUsage.objects.filter(item=item_id).order_by("id")
    subject_list = []
    for subject in subjects:
        subject_list.append(
            {
                "usage_id": subject.id,
                "type": subject.type,
                "subject": subject.subject,
            }
        )
    # subject_formset is "unbound" with this initial data
    subject_formset = SubjectUsageFormset(initial=subject_list, prefix="subjects")
    return subject_formset


def save_all_item_data(item_id: int, request: HttpRequest) -> None:
    CopyrightUsageFormset = formset_factory(
        CopyrightUsageForm, extra=1, can_delete=True
    )
    LanguageUsageFormset = formset_factory(LanguageUsageForm, extra=1, can_delete=True)
    NameUsageFormset = formset_factory(NameUsageForm, extra=1, can_delete=True)
    PublisherUsageFormset = formset_factory(
        PublisherUsageForm, extra=1, can_delete=True
    )
    ResourceUsageFormset = formset_factory(ResourceUsageForm, extra=1, can_delete=True)
    SubjectUsageFormset = formset_factory(SubjectUsageForm, extra=1, can_delete=True)
    item_form = ProjectItemForm(request.POST)
    copyright_formset = CopyrightUsageFormset(request.POST, prefix="copyrights")
    language_formset = LanguageUsageFormset(request.POST, prefix="languages")
    name_formset = NameUsageFormset(request.POST, prefix="names")
    publisher_formset = PublisherUsageFormset(request.POST, prefix="publishers")
    resource_formset = ResourceUsageFormset(request.POST, prefix="resources")
    subject_formset = SubjectUsageFormset(request.POST, prefix="subjects")

    # TODO: Better way to check validity of all forms, without unpacking request twice.
    if (
        item_form.is_valid()
        & copyright_formset.is_valid()
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
        # Item data
        item = ProjectItem.objects.get(pk=item_id)
        item.coverage = item_form.cleaned_data["coverage"]
        item.sequence = item_form.cleaned_data["sequence"]
        item.status = item_form.cleaned_data["status"]
        item.title = item_form.cleaned_data["title"]
        item.type = item_form.cleaned_data["type"]
        item.last_modified_date = timezone.now()
        item.last_modified_by = request.user
        item.save()
        # Other, optional, metadata types
        save_item_copyrights(item, copyright_formset.cleaned_data)
        save_item_languages(item, language_formset.cleaned_data)
        save_item_names(item, name_formset.cleaned_data)
        save_item_publishers(item, publisher_formset.cleaned_data)
        save_item_resources(item, resource_formset.cleaned_data)
        save_item_subjects(item, subject_formset.cleaned_data)


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


# TODO: Refactor save_item_XXXX() to minimize similar/identical code
def save_item_copyrights(item: ProjectItem, copyright_formset_data: list) -> None:
    # List of dictionaries, some/all of which can be empty
    for copyright_usage_data in copyright_formset_data:
        if valid_metadata_usage(copyright_usage_data):
            # Populate object
            copyright_usage = ItemCopyrightUsage(
                copyright=copyright_usage_data["copyright"],
                type=copyright_usage_data["type"],
                item=item,
            )
            # Existing object with real id
            if copyright_usage_data["usage_id"] > 0:
                copyright_usage.id = copyright_usage_data["usage_id"]
            # Only delete if record already exists; otherwise, just don't save
            if copyright_usage_data["DELETE"]:
                if copyright_usage.id:
                    copyright_usage.delete()
            else:
                copyright_usage.save()


# TODO: Refactor save_item_XXXX() to minimize similar/identical code
def save_item_languages(item: ProjectItem, language_formset_data: list) -> None:
    # List of dictionaries, some/all of which can be empty
    for language_usage_data in language_formset_data:
        if valid_metadata_usage(language_usage_data):
            # Populate object
            language_usage = ItemLanguageUsage(
                language=language_usage_data["language"],
                item=item,
            )
            # Existing object with real id
            if language_usage_data["usage_id"] > 0:
                language_usage.id = language_usage_data["usage_id"]
            # Only delete if record already exists; otherwise, just don't save
            if language_usage_data["DELETE"]:
                if language_usage.id:
                    language_usage.delete()
            else:
                language_usage.save()


# TODO: Refactor save_item_XXXX() to minimize similar/identical code
def save_item_names(item: ProjectItem, name_formset_data: list) -> None:
    # List of dictionaries, some/all of which can be empty
    for name_usage_data in name_formset_data:
        if valid_metadata_usage(name_usage_data):
            # Populate object
            name_usage = ItemNameUsage(
                name=name_usage_data["name"],
                type=name_usage_data["type"],
                item=item,
            )
            # Existing object with real id
            if name_usage_data["usage_id"] > 0:
                name_usage.id = name_usage_data["usage_id"]
            # Only delete if record already exists; otherwise, just don't save
            if name_usage_data["DELETE"]:
                if name_usage.id:
                    name_usage.delete()
            else:
                name_usage.save()


# TODO: Refactor save_item_XXXX() to minimize similar/identical code
def save_item_publishers(item: ProjectItem, publisher_formset_data: list) -> None:
    # List of dictionaries, some/all of which can be empty
    for publisher_usage_data in publisher_formset_data:
        if valid_metadata_usage(publisher_usage_data):
            # Populate object
            publisher_usage = ItemPublisherUsage(
                publisher=publisher_usage_data["publisher"],
                type=publisher_usage_data["type"],
                item=item,
            )
            # Existing object with real id
            if publisher_usage_data["usage_id"] > 0:
                publisher_usage.id = publisher_usage_data["usage_id"]
            # Only delete if record already exists; otherwise, just don't save
            if publisher_usage_data["DELETE"]:
                if publisher_usage.id:
                    publisher_usage.delete()
            else:
                publisher_usage.save()


# TODO: Refactor save_item_XXXX() to minimize similar/identical code
def save_item_resources(item: ProjectItem, resource_formset_data: list) -> None:
    # List of dictionaries, some/all of which can be empty
    for resource_usage_data in resource_formset_data:
        if valid_metadata_usage(resource_usage_data):
            # Populate object
            resource_usage = ItemResourceUsage(
                resource=resource_usage_data["resource"],
                type=resource_usage_data["type"],
                item=item,
            )
            # Existing object with real id
            if resource_usage_data["usage_id"] > 0:
                resource_usage.id = resource_usage_data["usage_id"]
            # Only delete if record already exists; otherwise, just don't save
            if resource_usage_data["DELETE"]:
                if resource_usage.id:
                    resource_usage.delete()
            else:
                resource_usage.save()


# TODO: Refactor save_item_XXXX() to minimize similar/identical code
def save_item_subjects(item: ProjectItem, subject_formset_data: list) -> None:
    # List of dictionaries, some/all of which can be empty
    for subject_usage_data in subject_formset_data:
        if valid_metadata_usage(subject_usage_data):
            # Populate object
            subject_usage = ItemSubjectUsage(
                subject=subject_usage_data["subject"],
                type=subject_usage_data["type"],
                item=item,
            )
            # Existing object with real id
            if subject_usage_data["usage_id"] > 0:
                subject_usage.id = subject_usage_data["usage_id"]
            # Only delete if record already exists; otherwise, just don't save
            if subject_usage_data["DELETE"]:
                if subject_usage.id:
                    subject_usage.delete()
            else:
                subject_usage.save()
