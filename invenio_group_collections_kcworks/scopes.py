# Part of Invenio-Group-Collections-KCWorks
# Copyright (C) 2023-2026, MESH Research
#
# Invenio-Group-Collections-KCWorks is free software; you can redistribute
# and/or modify it under the terms of the MIT License; see LICENSE file
# for more details.

"""OAuth scopes for the group-collections API."""

from invenio_i18n import lazy_gettext as _
from invenio_oauth2server.models import Scope

group_collections_read_scope = Scope(
    id_="group-collections:read",
    group="group-collections",
    help_text=_("Read group collections via the group-collections API."),
)

group_collections_write_scope = Scope(
    id_="group-collections:write",
    group="group-collections",
    help_text=_("Create, update, and delete group collections."),
)
