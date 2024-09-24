# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.


class CommonsGroupNotFoundError(Exception):
    pass


class CollectionAlreadyExistsError(Exception):
    pass


class CollectionNotFoundError(Exception):
    pass


class RoleNotCreatedError(Exception):
    pass


class CollectionNotCreatedError(Exception):
    pass
