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
from .api import GroupsMetadataAPI
from .service import GroupsMetadataService
from invenio_records_resources.services.base.config import (
    ConfiguratorMixin,
    FromConfig,
    FromConfigSearchOptions,
    SearchOptionsMixin,
)
from invenio_records_resources.services.records.config import RecordServiceConfig
from invenio_records_resources.services.records.results import (
    RecordItem, RecordList
)

class GroupsMetadataServiceConfig(RecordServiceConfig, ConfiguratorMixin):
    """Communities service configuration."""

    service_id = "groups_metadata"

    # Common configuration
    # permission_policy_cls = FromConfig(
    #     "GROUPS_PERMISSION_POLICY", default=CommunityPermissionPolicy
    # )
    # Record specific configuration
    record_cls = GroupsMetadataAPI
    result_item_cls = RecordItem
    result_list_cls = RecordList
    indexer_queue_name = "groups_metadata"

    # Search configuration
    # search = FromConfigSearchOptions(
    #     "COMMUNITIES_SEARCH",
    #     "COMMUNITIES_SORT_OPTIONS",
    #     "COMMUNITIES_FACETS",
    #     search_option_cls=SearchOptions,
    # )

    # Service schema
    # schema = CommunitySchema

    # links_item = {
    #     "self": CommunityLink("{+api}/communities/{id}"),
    #     "self_html": CommunityLink("{+ui}/communities/{slug}"),
    #     "settings_html": CommunityLink("{+ui}/communities/{slug}/settings"),
    #     "logo": CommunityLink("{+api}/communities/{id}/logo"),
    #     "rename": CommunityLink("{+api}/communities/{id}/rename"),
    #     "members": CommunityLink("{+api}/communities/{id}/members"),
    #     "public_members": CommunityLink("{+api}/communities/{id}/members/public"),
    #     "invitations": CommunityLink("{+api}/communities/{id}/invitations"),
    #     "requests": CommunityLink("{+api}/communities/{id}/requests"),
    #     "records": CommunityLink("{+api}/communities/{id}/records"),
    # }

    # action_link = CommunityLink(
    #     "{+api}/communities/{id}/{action_name}", when=can_perform_action
    # )

    # links_search = pagination_links("{+api}/communities{?args*}")
    # links_featured_search = pagination_links("{+api}/communities/featured{?args*}")
    # links_user_search = pagination_links("{+api}/user/communities{?args*}")
    # links_community_requests_search = pagination_links(
    #     "{+api}/communities/{community_id}/requests{?args*}"
    # )

    # Service components
    # components = FromConfig(
    #     "COMMUNITIES_SERVICE_COMPONENTS", default=DefaultCommunityComponents
    # )

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
        app.extensions["invenio-groups"] = self

    def init_service(self, app):
        """Initialize service."""
        self.service = GroupsMetadataService(GroupsMetadataServiceConfig.build(app))

    def init_config(self, app):
        """Initialize configuration.

        :param app: The Flask application.
        """
        for k in dir(config):
            if k.startswith("GROUPS_"):
                app.config.setdefault(k, getattr(config, k))
