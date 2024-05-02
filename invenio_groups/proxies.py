# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Proxy entities for invenio-groups."""

from flask import current_app
from werkzeug.local import LocalProxy

current_groups = LocalProxy(lambda: current_app.extensions["invenio-groups"])
"""Proxy to the extension."""

current_group_collections_service = LocalProxy(
    lambda: current_groups.collections_service
)
"""Proxy to the extension."""
