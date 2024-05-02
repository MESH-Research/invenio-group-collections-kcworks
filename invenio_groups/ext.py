# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Groups extension for Invenio."""

from invenio_groups.views import (
    GroupCollectionsResource,
    GroupCollectionsResourceConfig,
)
from . import config
from .service_config import (
    GroupCollectionsServiceConfig,
    GroupsMetadataServiceConfig,
)
from .service import (
    GroupCollectionsService,
    GroupsMetadataService,
)


class InvenioGroups(object):
    """Invenio-Groups extension."""

    def __init__(self, app=None, **kwargs):
        """Extension initialization."""
        if app:
            self._state = self.init_app(app, **kwargs)

    def init_app(self, app, **kwargs):
        """Flask application initialization.

        :param app: The Flask application.
        """
        self.init_config(app)
        self.init_service(app)
        self.init_resources(app)
        app.extensions["invenio-groups"] = self

    def init_service(self, app):
        """Initialize service."""
        self.service = GroupsMetadataService(
            GroupsMetadataServiceConfig.build(app)
        )
        self.collections_service = GroupCollectionsService(
            GroupCollectionsServiceConfig.build(app)
        )

    def init_config(self, app):
        """Initialize configuration.

        :param app: The Flask application.
        """
        for k in dir(config):
            if k.startswith("GROUPS_"):
                app.config.setdefault(k, getattr(config, k))
        for k in dir(config):
            if k.startswith("GROUP_COLLECTIONS_"):
                app.config.setdefault(k, getattr(config, k))

    def init_resources(self, app):
        """Initialize resources."""
        self.group_collections_resource = GroupCollectionsResource(
            GroupCollectionsResourceConfig(), service=self.collections_service
        )
