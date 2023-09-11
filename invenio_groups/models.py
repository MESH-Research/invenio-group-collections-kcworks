# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""SQLAlchemy db models for invenio-groups.
"""

from invenio_db import db
from invenio_records.models import RecordMetadataBase

class GroupsMetadata(db.Model, RecordMetadataBase):
    """SQLAlchemy model for a group.

    Metadata about a group is stored in the ``json`` field. The ``json`` field
    is a JSONB field in PostgreSQL and a TEXT field in SQLite. This metadata is decoded and available through the ``data`` property.

    A subclass depending on the basic record model defined in invenio_records.models. This base model provides the following fields:

    :id: UUID identifier for the record.
    :created: Timestamp for when the record was created. Inherted from
              RecordMetadataBase and set automatically.
    :updated: Timestamp for when the record was last updated. Inherted from
              RecordMetadataBase and set automatically.
    :json: JSON field for storing the record metadata.
    :version_id: Enables SQLAlchemy version counter (not the same as SQLAlchemy-Continuum)

    When you create a new ``Group`` the ``json`` field value should never be
    ``NULL``. Default value is an empty dict. ``NULL`` value means that the
    record metadata has been deleted.

    The ``json`` field includes the following properties common to all records:

    :is_deleted: Boolean flag to determine if a record is soft deleted.
                 Inherted from RecordMetadataBase and set automatically.

    The ``json`` field also includes the following properties holding metadata from the commons:

    :commons_id
    :group_name
    :group_url
    :privacy :public, private, or hidden
    :description
    :site_url
    :profile_image
    :who_can_upload :anyone, mods and admins, or admins only

    Finally, the ``json`` field includes one property with internal Invenio information:

    :invenio_roles :dictionary of commons group roles and their matching
                    Invenio roles

    The ``encoder`` Class-level attribute can be used to set a JSON data
    encoder/decoder. This allows you to, e.g., convert specific entries to
    complex Python objects. For instance you could convert ISO-formatted
    datetime objects into Python datetime objects.
    """

    __tablename__ = "groups_metadata"

    def __repr__(self) -> str:
        return f"<{self.__tablename__} {self.id}, json: {self.json}, created: {self.created}, updated: {self.updated}, version_id: {self.version_id}>"