# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Groups extension for Invenio.
"""

from . import config

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
        app.extensions["invenio-groups"] = self

    def init_config(self, app):
        """Initialize configuration.

        :param app: The Flask application.
        """
        for k in dir(config):
            if k.startswith("GROUPS_"):
                app.config.setdefault(k, getattr(config, k))
