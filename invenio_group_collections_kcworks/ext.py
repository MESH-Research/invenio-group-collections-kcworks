# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Extension providing collections administered by remote social groups
for InvenioRDM."""

from invenio_group_collections_kcworks.views import (
    GroupCollectionsResource,
    GroupCollectionsResourceConfig,
)
from . import config
from .service_config import (
    GroupCollectionsServiceConfig,
)
from .service import (
    GroupCollectionsService,
)


class InvenioGroupCollections(object):
    """invenio-group-collections-kcworks extension."""

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
        app.extensions["invenio-group-collections-kcworks"] = self

    def init_service(self, app):
        """Initialize service."""
        self.collections_service = GroupCollectionsService(
            GroupCollectionsServiceConfig.build(app)
        )

    def init_config(self, app):
        """Initialize configuration.

        :param app: The Flask application.
        """
        for k in dir(config):
            if k.startswith("GROUP_COLLECTIONS_"):
                app.config.setdefault(k, getattr(config, k))
        if not app.config.get("GROUP_COLLECTIONS_ADMIN_EMAIL"):
            app.config.setdefault(
                "GROUP_COLLECTIONS_ADMIN_EMAIL", app.config.get("ADMIN_EMAIL")
            )

    def init_resources(self, app):
        """Initialize resources."""
        self.group_collections_resource = GroupCollectionsResource(
            GroupCollectionsResourceConfig(), service=self.collections_service
        )
