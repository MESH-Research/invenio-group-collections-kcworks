# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""DB model interaction api for invenio-groups."""


from .models import Group
from invenio_records.api import Record

class GroupAPI(Record):
    """API class for interacting with group metadata records.
    """

    model_cls = Group