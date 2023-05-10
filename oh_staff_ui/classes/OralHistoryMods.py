from eulxml.xmlmap import mods
from eulxml.xmlmap.mods import MODS
from oh_staff_ui.models import ProjectItem
import logging

logger = logging.getLogger(__name__)


class OralHistoryMods(MODS):
    def __init__(self, project_item):
        super().__init__()
        self._item = project_item

    def populate_fields(self):
        self.title = self._item.title
        self._populate_identifier()

    def _populate_identifier(self):
        self.identifiers.extend([mods.Identifier(text=self._item.ark)])
