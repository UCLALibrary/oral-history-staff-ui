from django import forms


class ProjectItemForm(forms.Form):
    title = forms.CharField(
        required=True, max_length=256, widget=forms.TextInput(attrs={"size": 80})
    )
    sequence = forms.CharField(
        required=True, max_length=3, widget=forms.TextInput(attrs={"size": 3})
    )
