import logging
from django.db.models import Q
from django.forms import formset_factory
from django.http.request import HttpRequest  # for code completion
from django.utils import timezone
from oh_staff_ui.forms import ProjectItemForm, NameUsageForm
from oh_staff_ui.models import ProjectItem, ItemNameUsage

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


def get_all_item_data(item_id: int) -> dict:
    item = ProjectItem.objects.get(pk=item_id)
    names = ItemNameUsage.objects.filter(item=item_id).order_by("id")
    return {
        "item": item,
        "names": names,
    }


def get_edit_item_context(item_id: int) -> dict:
    NameUsageFormset = formset_factory(NameUsageForm, extra=1, can_delete=True)
    # Populate forms with data from database
    item_data = get_all_item_data(item_id)
    logger.info(f"{item_data=}")
    item = item_data["item"]
    names = item_data["names"]
    item_form = ProjectItemForm(
        {"title": item.title, "type": item.type, "sequence": item.sequence}
    )
    # Formset needs list of dictionaries of initial values.
    name_list = []
    for name in names:
        name_list.append(
            {
                "usage_id": name.id,
                "type": name.type,
                "name": name.name,
            }
        )
    name_formset = NameUsageFormset(initial=name_list, prefix="names")
    return {
        "item": item,
        "item_form": item_form,
        "name_formset": name_formset,
    }


def save_all_item_data(item_id: int, request: HttpRequest) -> None:
    NameUsageFormset = formset_factory(NameUsageForm, extra=1, can_delete=True)
    item_form = ProjectItemForm(request.POST)
    name_formset = NameUsageFormset(request.POST, prefix="names")

    if item_form.is_valid() & name_formset.is_valid():
        logger.info(f"Saving data for item {item_id}")
        logger.info(item_form.cleaned_data)
        logger.info(name_formset.cleaned_data)
        # Item data
        item = ProjectItem.objects.get(pk=item_id)
        item.sequence = item_form.cleaned_data["sequence"]
        item.title = item_form.cleaned_data["title"]
        item.type = item_form.cleaned_data["type"]
        item.last_modified_date = timezone.now()
        item.last_modified_by = request.user
        item.save()
        # Name usage data
        for name_usage_data in name_formset.cleaned_data:
            # List of dictionaries, some/all of which can be empty
            if name_usage_data:
                name_usage = ItemNameUsage(
                    name=name_usage_data["name"],
                    type=name_usage_data["type"],
                    item=item,
                )
                if name_usage_data["usage_id"] > 0:
                    name_usage.id = name_usage_data["usage_id"]
                if name_usage_data["DELETE"]:
                    # Only delete if record already exists; otherwise, just don't save
                    if name_usage.id:
                        name_usage.delete()
                else:
                    name_usage.save()
