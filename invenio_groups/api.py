# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""DB model interaction api for invenio-groups."""


from .models import GroupsMetadata
from invenio_db import db
from invenio_groups.validators import groups_metadata_schema
from invenio_groups.dumpers import IndexedAtDumperExt
from invenio_pidstore.errors import PIDDeletedError, PIDDoesNotExistError
from invenio_records.dumpers import SearchDumper
from invenio_records.systemfields import (
    ConstantField,
    DictField,
    ModelField,
    SystemField,
    SystemFieldsMixin,
    SystemFieldContext,
)
from invenio_records_resources.records.systemfields import (
    IndexField,
)  # , PIDField
from invenio_records_resources.records.api import (
    PersistentIdentifierWrapper,
    Record,
)
from uuid import UUID


class GroupPIDFieldContext(SystemFieldContext):
    """PID Slug Field Context."""

    def parse_pid(self, value):
        """Parse pid."""
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except (TypeError, ValueError):
            return value

    def resolve(self, pid_value, registered_only=True):
        """Resolve identifier (either uuid or slug)."""
        pid_value = self.parse_pid(pid_value)

        field_name = self.field._id_field

        with db.session.no_autoflush:  # avoid flushing the current session
            model = self.record_cls.model_cls.query.filter_by(
                **{field_name: pid_value}
            ).one_or_none()
            if model is None:
                raise PIDDoesNotExistError("comid", str(pid_value))
            record = self.record_cls(model.data, model=model)
            if record.is_deleted:
                raise PIDDeletedError(
                    PersistentIdentifierWrapper(pid_value), record
                )
            return record


class GroupPIDField(SystemField):
    """System field for managing record pid."""

    def __init__(self, id_field):
        """Create a new GroupPIDField instance."""
        self._id_field = id_field

    def obj(self, record):
        """Get the pid-like object from the record."""
        pid_value = getattr(record, self._id_field)
        if pid_value is None:
            return None
        return PersistentIdentifierWrapper(str(pid_value))

    def __get__(self, record, owner=None):
        """Get the record's pid object."""
        if record is None:
            # access by class
            return GroupPIDFieldContext(self, owner)
        # access by object
        return self.obj(record)

    #
    # Life-cycle hooks
    #
    def pre_commit(self, record):
        """Called before a record is committed."""
        # Make sure we don't dump the two model fields into the JSON of the
        # record.
        record.pop(self._id_field, None)


class GroupsMetadataAPI(Record, SystemFieldsMixin):
    """API class for interacting with group metadata records.

    `metadata` system field created by Record
    """

    id = ModelField()
    pid = GroupPIDField("id")  # removed from stored record data?
    model_cls = GroupsMetadata
    access = DictField(clear_none=True, create_if_missing=True)
    invenio_roles = DictField(clear_none=True, create_if_missing=True)

    # FIXME: This is a hack to get around the fact that the service _create
    # method tries to instantiate an API object with empty data before calling
    # the components which load the data that would validate against the schema.
    schema = ConstantField("$schema", groups_metadata_schema)
    # schema = ConstantField("$schema", "local://groups-metadata-v1.0.0.json")
    index = IndexField(
        "groups-groups-v1.0.0", search_alias="groups-groups-v1.0.0"
    )

    # format_checker = None
    # validator = None
    dumper = SearchDumper(
        extensions=[
            IndexedAtDumperExt(),
        ]
    )
    # loader = None
