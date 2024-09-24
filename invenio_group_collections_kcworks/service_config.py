# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Configuration class and helper classes for the groups_metadata service."""

from invenio_records_permissions.generators import (
    AnyUser,
    AuthenticatedUser,
    SystemProcess,
)
from invenio_records_permissions.policies import BasePermissionPolicy
from invenio_records_resources.services.base.config import (
    ConfiguratorMixin,
)
from invenio_records_resources.services.records.config import (
    RecordServiceConfig,
)


class GroupCollectionsPermissionPolicy(BasePermissionPolicy):
    """Permission policy for group collections."""

    can_create = [AuthenticatedUser(), SystemProcess()]
    can_update = [AuthenticatedUser(), SystemProcess()]
    can_read = [AnyUser(), SystemProcess()]
    can_delete = [AuthenticatedUser(), SystemProcess()]


class GroupCollectionsServiceConfig(RecordServiceConfig, ConfiguratorMixin):
    """Community collections service configuration."""

    service_id = "group_collections"
