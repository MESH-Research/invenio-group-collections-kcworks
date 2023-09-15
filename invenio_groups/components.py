# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Service components for the invenio-groups service.
"""

from invenio_records_resources.services.records.components import (
    ServiceComponent,
)

class InvenioRolesComponent(ServiceComponent):
    """Service component for custom fields."""

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """Inject parsed custom fields to the record."""
        record.invenio_roles = data.get("invenio_roles", {})

    def update(self, identity, data=None, record=None, **kwargs):
        """Inject parsed custom fields to the record."""
        record.invenio_roles = data.get("invenio_roles", {})


class AccessComponent(ServiceComponent):
    """Service component for custom fields."""

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """Inject parsed custom fields to the record."""
        record.access = data.get("access", {})

    def update(self, identity, data=None, record=None, **kwargs):
        """Inject parsed custom fields to the record."""
        record.access = data.get("access", {})
