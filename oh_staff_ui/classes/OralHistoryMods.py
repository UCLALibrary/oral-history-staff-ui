import logging
from eulxml.xmlmap import mods
from eulxml.xmlmap.mods import MODS
from oh_staff_ui.models import (
    Description,
    DescriptionType,
    ItemLanguageUsage,
    Format,
)

logger = logging.getLogger(__name__)


class OralHistoryMods(MODS):
    def __init__(self, project_item):
        super().__init__()
        self._item = project_item

    def populate_fields(self):
        # Elements used in MODS directly on the ProjectItem
        self._populate_title()
        self._populate_identifier()
        self._populate_relation()

        self._populate_language()
        self._populate_format()
        self._populate_description()

    def _populate_title(self):
        self.title = self._item.title

    def _populate_identifier(self):
        self.identifiers.extend([mods.Identifier(text=self._item.ark)])

    def _populate_relation(self):
        if self._item.relation:
            self.related_items.extend([mods.RelatedItem(title=self._item.relation)])

    def _populate_language(self):
        for ilu in ItemLanguageUsage.objects.filter(item=self._item):
            lang = mods.Language()
            lang.terms.append(mods.LanguageTerm(text=ilu.value))
            self.languages.append(lang)

    def _populate_format(self):
        format = Format.objects.filter(item=self._item).first()
        if format:
            self.create_physical_description()
            self.physical_description.extent = format.value

    def _populate_description(self):
        descriptions = Description.objects.filter(item=self._item)

        for desc in descriptions:
            desc_type = desc.type.type.lower()

            if desc_type == "abstract":
                self.create_abstract()
                self.abstract.text = desc.value

            elif desc_type in ["not qualified", "caption", "note"]:
                self.notes.append(mods.Note(text=desc.value))

            elif desc_type == "biographicalnote":
                self.notes.append(
                    mods.Note(
                        type="biographical",
                        label="Biographical Information",
                        text=desc.value,
                    )
                )

            elif desc_type == "adminnote":
                note_components = desc.value.split(":", 1)

                if len(note_components) <= 1:
                    self.notes.append(mods.Note(text=desc.value))

                else:
                    admin_note_type = note_components[0].lower()
                    admin_note_value = note_components[1]

                    if admin_note_type == "supporting documents":
                        self.notes.append(
                            mods.Note(
                                label="Supporting Documents",
                                type="supportingdocuments",
                                text=admin_note_value,
                            )
                        )

                    elif admin_note_type == "interviewer background and preperation":
                        self.notes.append(
                            mods.Note(
                                label="Interviewer Background and Preperation",
                                type="interviewerhistory",
                                text=admin_note_value,
                            )
                        )

                    elif admin_note_type == "processing of interview":
                        self.notes.append(
                            mods.Note(
                                label="Processing of Interview",
                                type="processinterview",
                                text=admin_note_value,
                            )
                        )

            else:
                self.notes.append(mods.Note(text=desc.value))
