# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Configuration class and helper classes for the groups_metadata service."""

from .api import GroupsMetadataAPI
from .components import AccessComponent, InvenioRolesComponent
from .schema import GroupsMetadataSchema
from invenio_records_permissions.generators import (
    AnyUser,
    AuthenticatedUser,
    Disable,
    SystemProcess,
)
from invenio_records_permissions.policies import BasePermissionPolicy
from invenio_records_resources.services.records.config import (
    SearchOptions as SearchOptionsBase
)
from invenio_records_resources.services.base import Link
from invenio_records_resources.services.base.config import (
    ConfiguratorMixin,
    FromConfig,
    FromConfigSearchOptions,
    SearchOptionsMixin,
)
from invenio_records_resources.services.records.config import (
    RecordServiceConfig
)
from invenio_records_resources.services.records.components import (
    DataComponent,
    MetadataComponent
)
from invenio_records_resources.services.records.results import (
    RecordItem, RecordList
)


class GroupsMetadataPermissionPolicy(BasePermissionPolicy):
    """Permission policy for communities."""

    can_create = [AuthenticatedUser(), SystemProcess()]
    can_update = [AuthenticatedUser(), SystemProcess()]
    can_read = [AnyUser(), SystemProcess()]
    can_delete = [AuthenticatedUser(), SystemProcess()]


class SearchOptions(SearchOptionsBase, SearchOptionsMixin):
    """Search options."""

    # sort_featured = {
    #     "title": _("Featured"),
    #     "fields": [
    #         {
    #             "featured.past": {
    #                 "order": "desc",
    #             }
    #         }
    #     ],
    # }

    # facets = {"type": facets.type, "visibility": facets.visibility}
    # params_interpreters_cls = [
    #     QueryStrParam,
    #     PaginationParam,
    #     CommunitiesSortParam,
    #     FacetsParam,
    # ]

class GroupsMetadataLink(Link):
    """Link variables setter for Community Members links."""

    @staticmethod
    def vars(record, vars):
        """Variables for the URI template."""
        vars.update(
            {
                "id": record.id
            }
        )

class GroupsMetadataItem(RecordItem):
    """Result record item for groups metadata."""

    @property
    def id(self):
        """Get the record's id."""
        return self._record.id


class GroupsMetadataServiceConfig(RecordServiceConfig, ConfiguratorMixin):
    """Communities service configuration."""

    service_id = "groups_metadata"

    # Common configuration
    permission_policy_cls = FromConfig(
        "GROUPS_PERMISSION_POLICY", default=GroupsMetadataPermissionPolicy
    )
    # Record specific configuration
    record_cls = GroupsMetadataAPI
    result_item_cls = GroupsMetadataItem
    result_list_cls = RecordList
    indexer_queue_name = "groups-metadata-v1.0.0"

    # Search configuration
    search = FromConfigSearchOptions(
        "GROUPS_SEARCH",
        "GROUPS_SORT_OPTIONS",
        "GROUPS_FACETS",
        search_option_cls=SearchOptions,
    )

    # Service schema
    schema = GroupsMetadataSchema

    # Service components: where actual record operations are implemented
    components = FromConfig(
        "GROUPS_METADATA_SERVICE_COMPONENTS", default=[
            DataComponent,
            MetadataComponent,
            AccessComponent,
            InvenioRolesComponent,

            # CustomFieldsComponent,
            # RelationsComponent,
            # OAISetComponent,
        ]
    )

    links_item = {
        "self": GroupsMetadataLink("{+api}/groups/{id}"),
    }
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
