from eulxml.xmlmap.mods import MODS

import logging

logger = logging.getLogger(__name__)


class OralHistoryMods(MODS):
    def __init__(self, ark):
        super().__init__()
        self._ark = ark
