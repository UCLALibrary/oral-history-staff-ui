from django import forms
from oh_staff_ui.models import ItemType


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
