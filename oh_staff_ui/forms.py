from django import forms
from oh_staff_ui.models import (
    ItemType,
    Name,
    NameType,
    Subject,
    SubjectType,
)


class ProjectItemForm(forms.Form):
    title = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 80})
    )
    type = forms.ModelChoiceField(
        required=True, queryset=ItemType.objects.all().order_by("type"), initial="Audio"
    )
    sequence = forms.CharField(
        required=True, max_length=3, widget=forms.TextInput(attrs={"size": 3})
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
