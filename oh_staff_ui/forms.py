import os
from django import forms
from django.core.cache import cache
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
    get_default_type,
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
        queryset=ItemType.objects.all().order_by("type"),
        initial=get_default_type,
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


# Used by FileUploadForm
OH_FILE_SOURCE = os.getenv("DJANGO_OH_FILE_SOURCE")


class FileUploadForm(forms.Form):
    file_group = forms.ModelChoiceField(
        queryset=MediaFileType.objects.all().order_by("file_type"),
        empty_label="Please select a file type:",
        label="File type:",
    )
    # FilePathField (at least) path gets cached automatically by Django at application startup.
    # There's no direct way to make it see changes to the filesystem; workaround from
    # https://stackoverflow.com/questions/30656653/suffering-stale-choices-for-filepathfield

    _file_name_kw = dict(
        path=OH_FILE_SOURCE,
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
