from django import forms
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
    Name,
    NameType,
    Publisher,
    PublisherType,
    Resource,
    ResourceType,
    Subject,
    SubjectType,
    get_default_status,
    get_default_type,
)


class ProjectItemForm(forms.Form):
    title = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 80})
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
        required=False, max_length=256, widget=forms.TextInput(attrs={"size": 80})
    )
    relation = forms.CharField(
        required=False, max_length=256, widget=forms.TextInput(attrs={"size": 80})
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
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 80})
    )


class AltIdForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=AltIdType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 80})
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
        widget=forms.Textarea(attrs={"cols": 70, "rows": 3}),
    )


class DateForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=DateType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    value = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 80})
    )


class FormatForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    value = forms.CharField(
        required=True, max_length=1024, widget=forms.TextInput(attrs={"size": 80})
    )
