#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024-2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Top-level pytest configuration for invenio-group-collections-kcworks tests.

Mirrors sibling KCWorks packages (`invenio-remote-user-data-kcworks`,
`invenio-record-importer-kcworks`):

1. `create_app` returns `invenio_app.factory.create_api` so REST blueprints
   under `invenio_base.api_apps` are wired without the UI app.
2. Shared `app_config` from `kcworks-test-fixtures` supplies the common
   baseline; this conftest only wraps package-specific keys.
3. Suite fixtures live in `tests.fixtures.*` (submodule). Module-local
   helpers/constants stay in the individual test modules that need them.
"""

from collections.abc import Generator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pytest
from invenio_app.factory import create_api as _create_app
from invenio_communities.communities.services.components import (
    CommunityAccessComponent as BaseCommunityAccessComponent,
)
from invenio_rdm_records.services.communities.components import (
    CommunityAccessComponent as RDMCommunityAccessComponent,
)
from invenio_rdm_records.services.communities.components import (
    CommunityServiceComponents,
)

# Vendored kcworks-test-fixtures checkout; not part of this package's suite.
collect_ignore = ["fixtures"]

pytest_plugins = (
    "celery.contrib.pytest",
    "tests.fixtures.app",
    "tests.fixtures.app_config",
    "tests.fixtures.bootstrap",
    "tests.fixtures.celery",
    "tests.fixtures.cli",
    "tests.fixtures.communities",
    "tests.fixtures.community_events",
    "tests.fixtures.custom_fields",
    "tests.fixtures.files",
    "tests.fixtures.fixtures",
    "tests.fixtures.frontend",
    "tests.fixtures.identifiers",
    "tests.fixtures.idms",
    "tests.fixtures.indexer_queues",
    "tests.fixtures.logging",
    "tests.fixtures.mail",
    "tests.fixtures.names",
    "tests.fixtures.records",
    "tests.fixtures.roles",
    "tests.fixtures.search",
    "tests.fixtures.search_provisioning",
    "tests.fixtures.uow",
    "tests.fixtures.users",
    "tests.fixtures.vocabularies.affiliations",
    "tests.fixtures.vocabularies.community_types",
    "tests.fixtures.vocabularies.date_types",
    "tests.fixtures.vocabularies.descriptions",
    "tests.fixtures.vocabularies.funding_and_awards",
    "tests.fixtures.vocabularies.languages",
    "tests.fixtures.vocabularies.licenses",
    "tests.fixtures.vocabularies.resource_types",
    "tests.fixtures.vocabularies.roles",
    "tests.fixtures.vocabularies.subjects",
    "tests.fixtures.vocabularies.title_types",
    "tests.pytest_plugins.pytest_live_status",
)


@pytest.fixture(scope="session", autouse=True)
def _patch_rdm_community_inclusion_access_check() -> Generator[None, None, None]:
    """Mirror KCWorks community-access patch for API-only create_api tests.

    Yields:
        None: Control returns after the patch is installed.
    """
    from invenio_rdm_records import requests as rdm_requests

    original = rdm_requests.community_inclusion.is_access_restriction_valid

    def _allow_all(_record, _community) -> bool:
        return True

    rdm_requests.community_inclusion.is_access_restriction_valid = _allow_all
    yield
    rdm_requests.community_inclusion.is_access_restriction_valid = original


@pytest.fixture(scope="module")
def app_config(app_config) -> dict[str, Any]:
    """Add package-specific keys onto the shared test defaults.

    Returns:
        The layered Flask/Invenio application config.
    """
    # Shared fixtures assume combined UI+API (`SITE_API_URL` ends in `/api`).
    # This suite uses `create_api`, which has no `/api` WSGI mount — drop it
    # so `SITE_API_URL` + blueprint paths match the test client's route table.
    parts = urlsplit(app_config["SITE_API_URL"])
    path = parts.path.rstrip("/")
    if path.endswith("/api"):
        path = path[: -len("/api")]
    app_config["SITE_API_URL"] = urlunsplit(
        (parts.scheme, parts.netloc, path or "", parts.query, parts.fragment)
    )

    idms_base = app_config["IDMS_BASE_API_URL"]
    app_config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"] = {
        "knowledgeCommons": {
            "title": "Knowledge Commons",
            "url": f"{idms_base}groups/",
            "token_name": "COMMONS_PROFILES_API_TOKEN",
            "placeholder_avatar": "mystery-group.png",
        },
    }
    app_config["REMOTE_USER_DATA_API_ENDPOINTS"] = {
        "knowledgeCommons": {
            "title": "Knowledge Commons",
            "users": {
                "remote_endpoint": f"{idms_base}members/",
                "remote_identifier": "id",
                "remote_method": "GET",
                "token_env_variable_label": "COMMONS_PROFILES_API_TOKEN",
            },
            "groups": {
                "remote_endpoint": f"{idms_base}groups/",
                "remote_identifier": "id",
                "remote_method": "GET",
                "token_env_variable_label": "COMMONS_PROFILES_API_TOKEN",
                "group_roles": {
                    "owner": ["administrator"],
                    "curator": ["editor", "moderator"],
                    "reader": ["member"],
                },
            },
            "entity_types": {
                "associations": {"events": ["associated"]},
                "users": {"events": ["created", "updated", "deleted"]},
                "groups": {"events": ["created", "updated", "deleted"]},
            },
        },
    }
    # Eager tasks keep group-collection create/delete synchronous in this suite.
    app_config["CELERY_TASK_ALWAYS_EAGER"] = True
    app_config["CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS"] = True
    app_config["COMMUNITIES_SERVICE_COMPONENTS"] = [
        BaseCommunityAccessComponent if c is RDMCommunityAccessComponent else c
        for c in CommunityServiceComponents
    ]
    return app_config


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory for API-only tests.

    Returns:
        The `create_api` factory from `invenio_app.factory`.
    """
    return _create_app
