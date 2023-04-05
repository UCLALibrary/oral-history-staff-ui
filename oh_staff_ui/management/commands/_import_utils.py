from csv import DictReader
from oh_staff_ui.models import (
    Name,
    AuthoritySource,
    Copyright,
    Publisher,
    Subject,
    Resource,
    Language,
)


def get_dicts_from_tsv(filepath=str) -> list:
    with open(filepath, mode="r") as f:
        dict_reader = DictReader(f, delimiter="\t")
        full_dicts = list(dict_reader)
    return full_dicts


def get_or_create_name(source=AuthoritySource, value=str) -> Name:
    if Name.objects.filter(source=source, value=value).exists():
        return Name.objects.get(source=source, value=value)
    else:
        name = Name(source=source, value=value)
        name.save()
        return name


def get_or_create_copyright(source=AuthoritySource, value=str) -> Copyright:
    if Copyright.objects.filter(source=source, value=value).exists():
        return Copyright.objects.get(source=source, value=value)
    else:
        copyright = Copyright(source=source, value=value)
        copyright.save()
        return copyright


def get_or_create_publisher(source=AuthoritySource, value=str) -> Publisher:
    if Publisher.objects.filter(source=source, value=value).exists():
        return Publisher.objects.get(source=source, value=value)
    else:
        publisher = Publisher(source=source, value=value)
        publisher.save()
        return publisher


def get_or_create_subject(source=AuthoritySource, value=str) -> Subject:
    if Subject.objects.filter(source=source, value=value).exists():
        return Subject.objects.get(source=source, value=value)
    else:
        subject = Subject(source=source, value=value)
        subject.save()
        return subject


def get_or_create_resource(source=AuthoritySource, value=str) -> Resource:
    if Resource.objects.filter(source=source, value=value).exists():
        return Resource.objects.get(source=source, value=value)
    else:
        resource = Resource(source=source, value=value)
        resource.save()
        return resource


def get_or_create_language(source=AuthoritySource, value=str) -> Language:
    if Language.objects.filter(source=source, value=value).exists():
        return Language.objects.get(source=source, value=value)
    else:
        language = Language(source=source, value=value)
        language.save()
        return language
