# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups
# Copyright (C) 2023-2024, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Utility functions for invenio-groups."""

import logging
import os
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s:%(levelname)s : %(message)s")

instance_path = os.environ.get("INVENIO_INSTANCE_PATH")
if not instance_path:
    instance_path = Path(__file__).parent.parent

log_file_path = Path(instance_path) / "logs" / "invenio-group-collections.log"

if not log_file_path.exists():
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    log_file_path.touch()

file_handler = logging.handlers.RotatingFileHandler(
    log_file_path,
    maxBytes=1000000,
    backupCount=5,
)
file_handler.setFormatter(formatter)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)


def make_group_slug(
    id: Union[str, int], group_name: str, instance_name: str
) -> Union[str, list]:
    """Create a slug from a group name."""
    #  FIXME: Implement returning a list of slugs if the group has
    #  soft deleted collections.
    return f'{instance_name}|{group_name.lower().replace(" ", "-").replace(",", "")}'
