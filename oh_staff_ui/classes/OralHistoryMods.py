import logging
from django.conf import settings
from pathlib import Path
from eulxml import xmlmap
from eulxml.xmlmap import mods
from eulxml.xmlmap.mods import MODSv34
from eulxml.xmlmap.mods import Common
from oh_staff_ui.models import (
    AltTitle,
    AltId,
    Date,
    Description,
    Format,
    ItemCopyrightUsage,
    ItemLanguageUsage,
    ItemNameUsage,
    ItemSubjectUsage,
    MediaFile,
    ProjectItem,
)


logger = logging.getLogger(__name__)


class OralHistoryMods(MODSv34):
    def __init__(self, project_item):
        super().__init__()
        self._item = project_item
        self.populate_fields()

    def populate_fields(self):
        self._populate_titles()
        self._populate_create_date()
        self._populate_description()
        self._populate_format()
        self._populate_identifier()
        self._populate_language()
        self._populate_name()
        self._populate_relation()
        self._populate_rights()
        self._populate_subjects()
        self._populate_constituent_audio()
        self._populate_interviewee_image()
        self._populate_interview_content()
        self._populate_series_content()

    def _populate_titles(self):
        # create_title_info() should not be called, otherwise an empty duplicate title
        # container will be created, overwriting previous titles
        self.title_info_list.append(mods.TitleInfo(title=self._item.title))

        alt_titles = AltTitle.objects.filter(item=self._item)
        for alt_title in alt_titles:
            self.title_info_list.append(
                mods.TitleInfo(title=alt_title, type="alternative")
            )

    def _populate_identifier(self):
        # Always add Ark as identifier
        self.identifiers.append(mods.Identifier(text=self._item.ark))
        # If we have other AltIds, add with type
        alt_ids = AltId.objects.filter(item=self._item)
        for alt_id in alt_ids:
            self.identifiers.append(
                mods.Identifier(text=alt_id.value, type=alt_id.type.type)
            )

    def _populate_language(self):
        for ilu in ItemLanguageUsage.objects.filter(item=self._item):
            lang = mods.Language()
            lang.terms.append(mods.LanguageTerm(text=ilu.value))
            self.languages.append(lang)

    def _populate_name(self):
        for inu in ItemNameUsage.objects.filter(item=self._item):
            name = mods.Name()
            name.name_parts.append(mods.NamePart(text=inu.value.value))
            name.roles.append(mods.Role(type="text", text=inu.type.type))
            self.names.append(name)

    def _populate_relation(self):
        if self._item.relation:
            self.related_items.append(mods.RelatedItem(title=self._item.relation))

    def _populate_rights(self):
        # Following previous MODS generation process, accessRights is used with no type assignment
        for copyright in ItemCopyrightUsage.objects.filter(item=self._item):
            self.access_conditions.append(mods.AccessCondition(text=copyright.value))

    def _populate_subjects(self):
        subs_to_exclude = [
            "Arts, Literature, Music, and Film",
            "Donated Oral Histories",
            "Latinas and Latinos in Music",
            "Latinas and Latinos in Politics",
            "Mexican American Civil Rights",
        ]
        for isu in ItemSubjectUsage.objects.filter(item=self._item).exclude(
            value__value__in=subs_to_exclude
        ):
            self.subjects.append(
                mods.Subject(
                    authority=isu.value.source.source.lower(), topic=isu.value.value
                )
            )

    def _populate_format(self):
        format = Format.objects.filter(item=self._item).first()
        if format:
            self.create_physical_description()
            self.physical_description.extent = format.value

    def _populate_description(self):
        # Exclude adminnote and tableOfContents types from query entirely
        descriptions = Description.objects.filter(item=self._item).exclude(
            type__type__in=["adminnote", "tableOfContents"]
        )

        # Similar note element behaving qualifiers
        type_labels = {
            "biographicalnote": "Biographical Information",
            "interviewerhistory": "Interviewer Background and Preparation",
            "personpresent": "Persons Present",
            "place": "Place Conducted",
            "processinterview": "Processing of Interview",
            "supportingdocuments": "Supporting Documents",
        }

        for desc in descriptions:
            desc_type = desc.type.type.lower()

            if desc_type == "abstract":
                self.create_abstract()
                self.abstract.text = desc.value

            elif desc_type in type_labels.keys():
                type_value = (
                    "biographical" if desc_type == "biographicalnote" else desc_type
                )
                self.notes.append(
                    mods.Note(
                        type=type_value, label=type_labels[desc_type], text=desc.value
                    )
                )

            else:
                # Remaining 'note' types or non-matching get element with no type
                self.notes.append(mods.Note(text=desc.value))

    def _populate_create_date(self):
        dates = Date.objects.filter(item=self._item, type__type__exact="creation")

        for date in dates:
            self.create_origin_info()
            self.origin_info.created.append(mods.DateCreated(date=date))

    def _populate_constituent_audio(self):
        # For each Completed child of the item, get submaster audio MediaFile
        for child in ProjectItem.objects.filter(
            parent=self._item,
            status__status__in=["Completed", "Completed with minimal metadata"],
        ).order_by("sequence"):
            for audiofile in MediaFile.objects.filter(
                item=child, file_type__file_code="audio_submaster"
            ):
                self.related_items.append(self._create_relateditem_audio(audiofile))

    def _create_relateditem_audio(self, mi: MediaFile) -> MODSv34:
        pi = mi.item
        ri = RelatedItemOH(href=mi.file_url, type="constituent")
        ri.title = pi.title
        ri.identifiers.append(mods.Identifier(text=pi.ark))
        ri.parts.append(PartOH(order=pi.sequence, type="session_audio"))

        for toc in Description.objects.filter(item=pi, type__type="tableOfContents"):
            ri.toc = TableOfContents(text=toc.value)

        for ts in MediaFile.objects.filter(
            item=pi, file_type__file_code="text_master_transcript"
        ):
            # Add only for submasters, the public-access copy
            if ts.file_url.endswith("submaster.xml"):
                # Due to legacy design the text_master_transcript can have 2 file types
                # associated with it, we only want to show xml (TEI), and ignore html files
                ri.locations.append(LocationOH(url=ts.file_url, usage="timed log"))

        return ri

    def _populate_interviewee_image(self):
        for img in MediaFile.objects.filter(
            item=self._item, file_type__file_code="image_submaster"
        ).order_by("sequence"):
            self.locations.append(
                LocationOH(url=img.file_url, label="Image of Interviewee")
            )

    def _populate_interview_content(self):
        fc_to_label = {
            "pdf_master": "Interview Full Transcript (PDF)",
            "text_master_transcript": "Interview Full Transcript",
            "text_master_biography": "Interviewee Biography",
            "text_master_interview_history": "Interview History",
            "pdf_master_appendix": "Appendix to Interview",
            "text_master_appendix": "Appendix to Interview",
            "pdf_master_resume": "Narrator's Resume",
        }

        for f in MediaFile.objects.filter(
            item=self._item, file_type__file_code__in=fc_to_label.keys()
        ).order_by("sequence"):
            # Add only for submasters, the public-access copy
            if "submaster" in f.file_url:
                label = fc_to_label[f.file_type.file_code]
                usage = ""

                if f.file_type.file_code == "text_master_transcript":
                    if f.file_name_only.endswith(".html"):
                        label = f"{label} (Printable Version)"
                    else:
                        label = f"{label} (TEI/P5 XML)"
                        usage = "timed log"

                # If our MediaFile is TEI/P5 XML, a usage attribute is populated
                # and should be included
                if usage:
                    self.locations.append(
                        LocationOH(url=f.file_url, label=label, usage=usage)
                    )
                else:
                    self.locations.append(LocationOH(url=f.file_url, label=label))

    def _populate_series_content(self):
        p = self._item.parent
        if p and p.type.type.lower() == "series":
            ri = mods.RelatedItem(type="series")
            ri.title = p.title
            ri.identifiers.append(mods.Identifier(text=p.ark))

            for d in Description.objects.filter(item=p, type__type="abstract"):
                ri.create_abstract()
                ri.abstract.text = d.value

            self.related_items.append(ri)

    def write_mods_record(self):
        p = Path(f"{settings.MEDIA_ROOT}/{settings.OH_STATIC}/mods")
        p.mkdir(exist_ok=True, parents=True)

        with open(f"{p}/{self._item.ark_ns}-mods.xml", "wb") as mods_file:
            mods_file.write(self.serializeDocument(pretty=True))
            logger.info(
                f"Wrote MODS for item id: {self._item.id} to file: {self._item.ark_ns}-mods.xml"
            )


# Extended classes to supply some additional attributes not in stock library that we use


class LocationOH(mods.Location):
    label = xmlmap.StringField("@displayLabel")
    usage = xmlmap.StringField("mods:url/@usage")


class PartOH(mods.Part):
    order = xmlmap.StringField("@order")


class TableOfContents(Common):
    ROOT_NAME = "tableOfContents"
    text = xmlmap.StringField("text()")


class RelatedItemOH(mods.RelatedItem):
    MODSv34.ROOT_NAMESPACES["xlink"] = "http://www.w3.org/1999/xlink"
    href = xmlmap.StringField("@xlink:href")
    toc = xmlmap.NodeField("mods:tableOfContents", TableOfContents)
