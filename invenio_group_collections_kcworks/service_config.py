#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024-2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Configuration class and helper classes for the groups_metadata service."""

from invenio_records_resources.services.base.config import (
    ConfiguratorMixin,
)
from invenio_records_resources.services.records.config import (
    RecordServiceConfig,
)

from .permissions import GroupCollectionsPermissionPolicy


class GroupCollectionsServiceConfig(RecordServiceConfig, ConfiguratorMixin):
    """Community collections service configuration."""

    service_id = "group_collections"
    permission_policy_cls = GroupCollectionsPermissionPolicy
