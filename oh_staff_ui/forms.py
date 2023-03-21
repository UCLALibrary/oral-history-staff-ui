from django import forms
from oh_staff_ui.models import (
    Copyright,
    CopyrightType,
    ItemStatus,
    ItemType,
    Language,
    Name,
    NameType,
    Publisher,
    PublisherType,
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
    name = forms.ModelChoiceField(
        queryset=Name.objects.all().order_by("value"),
        empty_label="Please select a name:",
    )


class SubjectUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=SubjectType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all().order_by("value"),
        empty_label="Please select a subject:",
    )


class PublisherUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=PublisherType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    publisher = forms.ModelChoiceField(
        queryset=Publisher.objects.all().order_by("value"),
        empty_label="Please select a publisher:",
    )


class CopyrightUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    type = forms.ModelChoiceField(
        queryset=CopyrightType.objects.all().order_by("type"),
        empty_label="Please select a qualifier:",
    )
    copyright = forms.ModelChoiceField(
        queryset=Copyright.objects.all().order_by("value"),
        empty_label="Please select a copyright:",
    )


class LanguageUsageForm(forms.Form):
    usage_id = forms.IntegerField(initial=0, widget=forms.HiddenInput())
    language = forms.ModelChoiceField(
        queryset=Language.objects.all().order_by("language"),
        empty_label="Please select a language:",
    )
