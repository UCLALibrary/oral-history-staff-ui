from django import forms
from django.conf import settings
from django.core.cache import cache
from django.db.models import QuerySet
from oh_staff_ui.models import (
    AltIdType,
    AltTitleType,
    Copyright,
    CopyrightType,
    DateType,
    DescriptionType,
    ItemStatus,
    ItemType,
    Language,
    MediaFileType,
    Name,
    NameType,
    ProjectItem,
    Publisher,
    PublisherType,
    Resource,
    ResourceType,
    Subject,
    SubjectType,
    get_default_status,
)


class ProjectItemChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, item):
        return f"{item.title} ({item.ark})"


class ProjectItemForm(forms.Form):
    parent = ProjectItemChoiceField(
        required=False,
        queryset=(
            ProjectItem.objects.filter(type__type__in=["Series", "Interview"])
        ).order_by("title"),
    )
    title = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 140})
    )
    type = forms.ModelChoiceField(
        required=True,
        # Filter this dynamically via view and override of this form's __init__().
        queryset=ItemType.objects.all(),
    )
    sequence = forms.CharField(
        required=True, max_length=3, widget=forms.TextInput(attrs={"size": 3})
    )
    coverage = forms.CharField(
        required=False, max_length=256, widget=forms.TextInput(attrs={"size": 140})
    )
    relation = forms.CharField(
        required=False, max_length=256, widget=forms.TextInput(attrs={"size": 140})
    )
    status = forms.ModelChoiceField(
        required=True,
        queryset=ItemStatus.objects.all().order_by("status"),
        initial=get_default_status,
    )

    def __init__(self, *args, **kwargs) -> None:
        # If parent_item was explicitly passed, get it.
        # Must be pulled out (via pop()) before super()__init__() is called.
        parent_item = kwargs.pop("parent_item", None)
        # If it wasn't, try getting it from data {} passed to the form;
        # this is set by view_utils.get_edit_item_context().
        if kwargs.get("data"):
            parent_item = kwargs["data"].get("parent")
        # Now that we have parent_item, call super init.
        super().__init__(*args, **kwargs)
        # Get context-specific item types, based on parent.
        item_types = self._get_relevant_item_types(parent_item)
        # Set the "type" field to use these types.
        self.fields["type"].queryset = item_types
        # Default to the first value in the queryset, which will always have at least one value.
        self.fields["type"].initial = item_types[0]

    def _get_relevant_item_types(
        self, parent_item: ProjectItem | None = None
    ) -> QuerySet:
        """Get item types which are relevant to the item context.

        If no parent item, this is top-level: Series.
        If parent item is Series, this is 2nd-level: Interview.
        If parent item is Interview, this is 3rd-level: Audio or Video.
        """
        if parent_item is None:
            item_types = ["Series"]
        elif parent_item.type.type == "Series":
            item_types = ["Interview"]
        elif parent_item.type.type == "Interview":
            item_types = ["Audio", "Video"]
        return ItemType.objects.filter(type__in=item_types).order_by("type")


class ItemSearchForm(forms.Form):
    search_types = [("ark", "ARK"), ("title", "Title")]
    search_type = forms.ChoiceField(choices=search_types)
    query = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 80})
    )


class NameUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=NameType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.ModelChoiceField(
        queryset=Name.objects.all().order_by("value"),
        empty_label="Please select a name:",
    )


class SubjectUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=SubjectType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.ModelChoiceField(
        queryset=Subject.objects.all().order_by("value"),
        empty_label="Please select a subject:",
    )


class PublisherUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=PublisherType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.ModelChoiceField(
        queryset=Publisher.objects.all().order_by("value"),
        empty_label="Please select a publisher:",
    )


class CopyrightUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=CopyrightType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.ModelChoiceField(
        queryset=Copyright.objects.all().order_by("value"),
        empty_label="Please select a copyright:",
    )


class LanguageUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    value = forms.ModelChoiceField(
        queryset=Language.objects.all().order_by("value"),
        empty_label="Please select a language:",
    )


class ResourceUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=ResourceType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.ModelChoiceField(
        queryset=Resource.objects.all().order_by("value"),
        empty_label="Please select a resource:",
    )


class AltTitleForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=AltTitleType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 100})
    )


class AltIdForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=AltIdType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 100})
    )


class DescriptionForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=DescriptionType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.CharField(
        required=True,
        max_length=1024,
        widget=forms.Textarea(attrs={"cols": 98, "rows": 3}),
    )


class DateForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=DateType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 100})
    )


class FormatForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    value = forms.CharField(
        required=True, max_length=1024, widget=forms.TextInput(attrs={"size": 100})
    )


class FileUploadForm(forms.Form):
    file_type = forms.ModelChoiceField(
        queryset=MediaFileType.objects.all().order_by("file_type"),
        empty_label="Please select a file type:",
        label="File type:",
    )
    # FilePathField (at least) path gets cached automatically by Django at application startup.
    # There's no direct way to make it see changes to the filesystem; workaround from
    # https://stackoverflow.com/questions/30656653/suffering-stale-choices-for-filepathfield

    _file_name_kw = dict(
        path=settings.OH_FILE_SOURCE,
        recursive=True,
        allow_files=True,
        allow_folders=False,
        label="File:",
    )
    file_name = forms.FilePathField(**_file_name_kw)

    # __init__ is called every time the form is needed.
    # Cache values for 5 seconds (arbitrary); use cache if populated,
    # otherwise start fresh.
    def __init__(self, *args, **kwargs):
        seconds_to_cache = 5
        key = "file_name-cache-key"
        choices = cache.get(key)
        if not choices:
            field = forms.FilePathField(**self._file_name_kw)
            choices = field.choices
            cache.set(key, choices, seconds_to_cache)

        super().__init__(*args, **kwargs)
        self.base_fields["file_name"].choices = choices
