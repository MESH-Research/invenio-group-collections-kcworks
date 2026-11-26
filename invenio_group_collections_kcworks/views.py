#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Views for Commons group collections API endpoints."""

from typing import Any, NoReturn

import marshmallow as ma
import requests
from flask import (
    Blueprint,
    Flask,
    Response,
    g,
    jsonify,
)
from flask import current_app as app
from flask_resources import (
    JSONDeserializer,
    JSONSerializer,
    RequestBodyParser,
    Resource,
    ResourceConfig,
    ResponseHandler,
    from_conf,
    request_body_parser,
    request_parser,
    resource_requestctx,
    route,
)
from invenio_communities.errors import CommunityDeletedError
from invenio_oauth2server.decorators import require_api_auth, require_oauth_scopes
from invenio_records_resources.services.errors import PermissionDeniedError
from werkzeug.exceptions import (  # Unauthorized,
    BadRequest,
    Forbidden,
    MethodNotAllowed,
    NotFound,
    RequestTimeout,
    UnprocessableEntity,
)

from .errors import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    CommonsGroupNotFoundError,
)
from .proxies import current_group_collections_service
from .scopes import (
    group_collections_read_scope,
    group_collections_write_scope,
)
from .service import GroupCollectionsService


class GroupCollectionsResourceConfig(ResourceConfig):
    """Configuration for the group collections API resource."""

    blueprint_name = "group_collections"

    url_prefix = "/group_collections"

    error_handlers = {}

    default_accept_mimetype = "application/json"

    default_content_type = "application/json"

    response_handlers = {"application/json": ResponseHandler(JSONSerializer())}

    request_body_parsers = {"application/json": RequestBodyParser(JSONDeserializer())}


class GroupCollectionsResource(Resource):
    """Resource for Commons group collections API endpoints."""

    def __init__(
        self, config: GroupCollectionsResourceConfig, service: GroupCollectionsService
    ) -> None:
        """Constructor."""
        super().__init__(config)
        self.service = service

    error_handlers = {
        Forbidden: lambda e: (
            {"message": str(e), "status": 403},
            403,
        ),
        PermissionDeniedError: lambda e: (
            {"message": str(e) or "Permission denied.", "status": 403},
            403,
        ),
        MethodNotAllowed: lambda e: (
            {"message": str(e), "status": 405},
            405,
        ),
        NotFound: lambda e: (
            {"message": str(e), "status": 404},
            404,
        ),
        CommonsGroupNotFoundError: lambda e: (
            {"message": str(e), "status": 404},
            404,
        ),
        BadRequest: lambda e: (
            {"message": str(e), "status": 400},
            400,
        ),
        ma.ValidationError: lambda e: (
            {"message": str(e), "status": 400},
            400,
        ),
        UnprocessableEntity: lambda e: (
            {"message": str(e), "status": 422},
            422,
        ),
        RuntimeError: lambda e: (
            {"message": str(e), "status": 500},
            500,
        ),
        CollectionAlreadyExistsError: lambda e: (
            {"message": str(e), "status": 409},
            409,
        ),
        CollectionNotFoundError: lambda e: (
            {"message": str(e), "status": 404},
            404,
        ),
        CommunityDeletedError: lambda e: (
            {"message": "The collection has been deleted.", "status": 410},
            410,
        ),
        requests.exceptions.ConnectionError: lambda e: (
            {"message": str(e), "status": 503},
            503,
        ),
        RequestTimeout: lambda e: (
            {"message": str(e), "status": 503},
            503,
        ),
        NotImplementedError: lambda e: (
            {"message": str(e), "status": 501},
            501,
        ),
    }

    request_data = request_body_parser(
        parsers=from_conf("request_body_parsers"),
        default_content_type=from_conf("default_content_type"),
    )

    request_parsed_view_args = request_parser(
        {
            "slug": ma.fields.String(),
        },
        location="view_args",
    )

    request_parsed_args = request_parser(
        {
            "commons_instance": ma.fields.String(),
            "commons_group_id": ma.fields.String(),
            "collection": ma.fields.String(),
            "page": ma.fields.Integer(load_default=1),
            "size": ma.fields.Integer(
                validate=ma.validate.Range(min=4, max=1000), load_default=25
            ),
            "sort": ma.fields.String(
                validate=ma.validate.OneOf([
                    "newest",
                    "oldest",
                    "updated-desc",
                    "updated-asc",
                ]),
                load_default="updated-desc",
            ),
            "restore_deleted": ma.fields.Boolean(load_default=False),
        },
        location="args",
        unknown=ma.RAISE,
    )

    def create_url_rules(self) -> list[dict[str, Any]]:
        """Create the URL rules for the record resource.

        Returns:
            The list of Flask route rules for this resource.
        """
        return [
            route("POST", "/", self.create),
            route("GET", "/", self.search),
            route("GET", "/<slug>", self.read),
            route("DELETE", "/", self.failed_delete),
            route("DELETE", "/<slug>", self.delete),
            route("PATCH", "/<slug>/associate", self.associate),
            route("PATCH", "/<slug>/transfer", self.transfer),
            route("PATCH", "/<slug>", self.change_group_ownership),
            route("PUT", "/<slug>", self.replace_group_metadata),
        ]

    @require_api_auth()
    @require_oauth_scopes(group_collections_write_scope.id)
    def replace_group_metadata(self) -> NoReturn:
        """Reject metadata modification at this endpoint.

        Raises:
            NotImplementedError: Always; use the main `communities` API instead.
        """
        raise NotImplementedError(
            "Modification of collection metadata is not supported at "
            "this endpoint. Use the main `communities` API endpoint instead."
        )

    @require_api_auth()
    @require_oauth_scopes(group_collections_read_scope.id)
    @request_parsed_view_args
    def read(self) -> tuple[Response, int]:
        """Read a group collection by slug.

        Returns:
            JSON collection payload and HTTP 200.

        Raises:
            BadRequest: If no collection slug is provided.
        """
        collection_slug = resource_requestctx.view_args.get("slug")
        if collection_slug:
            collection = current_group_collections_service.read(
                g.identity, collection_slug
            )
            return jsonify(collection.to_dict()), 200
        else:
            raise BadRequest("No collection slug provided")

    @require_api_auth()
    @require_oauth_scopes(group_collections_read_scope.id)
    @request_parsed_args
    def search(self) -> tuple[Response, int]:
        """Search group collections.

        Returns:
            JSON search results and HTTP 200.
        """
        commons_instance = (
            resource_requestctx.args.get("commons_instance") or "knowledgeCommons"
        )
        commons_group_id = resource_requestctx.args.get("commons_group_id")
        page = resource_requestctx.args.get("page")
        size = resource_requestctx.args.get("size")
        sort = resource_requestctx.args.get("sort", "updated-desc")

        results = current_group_collections_service.search(
            g.identity,
            commons_instance,
            commons_group_id,
            sort=sort,
            size=size,
            page=page,
        )

        return jsonify(results.to_dict()), 200

    @require_api_auth()
    @require_oauth_scopes(group_collections_write_scope.id)
    @request_parsed_args
    @request_data
    def create(self) -> tuple[Response, int]:
        """Create a group collection for a Commons group.

        Returns:
            JSON create response and HTTP 201.
        """
        commons_instance = (
            resource_requestctx.data.get("commons_instance") or "knowledgeCommons"
        )
        commons_group_id = resource_requestctx.data.get("commons_group_id")
        restore_deleted = resource_requestctx.args.get("restore_deleted")
        collection_visibility = resource_requestctx.data.get("collection_visibility")

        new_collection = current_group_collections_service.create(
            g.identity,
            commons_group_id,
            commons_instance,
            restore_deleted=restore_deleted,
            collection_visibility=collection_visibility,
        )

        # Construct the response
        response_data = {
            "commons_group_id": commons_group_id,
            "collection": new_collection.data["slug"],
            "collection_id": new_collection.data["id"],
        }

        return jsonify(response_data), 201

    @require_api_auth()
    @require_oauth_scopes(group_collections_write_scope.id)
    @request_parsed_view_args
    @request_data
    def associate(self) -> tuple[Response, int]:
        """Associate an existing collection with a KC group.

        Returns:
            JSON associate response and HTTP 200.

        Raises:
            BadRequest: If no collection slug is provided.
        """
        collection_slug = resource_requestctx.view_args.get("slug")
        if not collection_slug:
            raise BadRequest("No collection slug provided")

        commons_instance = (
            resource_requestctx.data.get("commons_instance") or "knowledgeCommons"
        )
        commons_group_id = resource_requestctx.data.get("commons_group_id")
        collection_visibility = resource_requestctx.data.get(
            "collection_visibility"
        )

        updated = current_group_collections_service.associate(
            g.identity,
            collection_slug,
            commons_group_id,
            commons_instance,
            collection_visibility=collection_visibility,
        )
        return (
            jsonify({
                "commons_group_id": commons_group_id,
                "collection": updated.data["slug"],
                "collection_id": updated.data["id"],
            }),
            200,
        )

    @require_api_auth()
    @require_oauth_scopes(group_collections_write_scope.id)
    @request_parsed_view_args
    @request_data
    def transfer(self) -> tuple[Response, int]:
        """Transfer a linked collection to a different KC group.

        Returns:
            JSON transfer response and HTTP 200.

        Raises:
            BadRequest: If no collection slug is provided.
        """
        collection_slug = resource_requestctx.view_args.get("slug")
        if not collection_slug:
            raise BadRequest("No collection slug provided")

        commons_instance = (
            resource_requestctx.data.get("commons_instance") or "knowledgeCommons"
        )
        commons_group_id = resource_requestctx.data.get("commons_group_id")
        old_commons_instance = resource_requestctx.data.get(
            "old_commons_instance"
        )
        old_commons_group_id = resource_requestctx.data.get(
            "old_commons_group_id"
        )
        collection_visibility = resource_requestctx.data.get(
            "collection_visibility"
        )

        updated = current_group_collections_service.transfer(
            g.identity,
            collection_slug,
            commons_group_id,
            commons_instance,
            old_commons_group_id=old_commons_group_id,
            old_commons_instance=old_commons_instance,
            collection_visibility=collection_visibility,
        )
        return (
            jsonify({
                "commons_group_id": commons_group_id,
                "old_commons_group_id": old_commons_group_id,
                "collection": updated.data["slug"],
                "collection_id": updated.data["id"],
            }),
            200,
        )

    @require_api_auth()
    @require_oauth_scopes(group_collections_write_scope.id)
    def change_group_ownership(self) -> NoReturn:
        """Legacy PATCH /<slug> — use /associate or /transfer instead."""
        raise NotImplementedError(
            "PATCH /group_collections/<slug> is not supported. "
            "Use PATCH /group_collections/<slug>/associate or "
            "PATCH /group_collections/<slug>/transfer."
        )

    @require_api_auth()
    @require_oauth_scopes(group_collections_write_scope.id)
    @request_parsed_args
    @request_parsed_view_args
    def delete(self) -> tuple[str, int]:
        """Delete a group collection and delete the group roles.

        This is a soft delete operation. The collection is marked as deleted
        and a tombstone record is created. The group roles are also deleted.

        Returns:
            Success message and HTTP 204.

        Raises:
            BadRequest: If the collection slug or `commons_group_id` is missing.
        """
        collection_slug = resource_requestctx.view_args.get("slug")
        commons_instance = (
            resource_requestctx.args.get("commons_instance") or "knowledgeCommons"
        )
        commons_group_id = resource_requestctx.args.get("commons_group_id")
        app.logger.info(
            f"Attempting to delete collection {collection_slug} for "
            f"{commons_instance} group {commons_group_id}"
        )

        if not collection_slug:
            app.logger.error("No collection slug provided. Could not delete.")
            raise BadRequest("No collection slug provided")
        elif not commons_group_id:
            app.logger.error("No commons_group_id provided. Could not delete.")
            raise BadRequest("No commons_group_id provided")

        deleted_collection = current_group_collections_service.delete(
            g.identity,
            collection_slug,
            commons_instance,
            commons_group_id,
        )

        # Return appropriate response status
        return (
            f"Successfully deleted collection "
            f"{deleted_collection.data['slug']} "
            f"along with its user roles for {commons_instance} group "
            f"{commons_group_id}",
            204,
        )

    def failed_delete(self) -> NoReturn:
        """Error response for missing collection slug.

        Raises:
            BadRequest: Always, because no collection slug was provided.
        """
        raise BadRequest("No collection slug provided")


def create_api_blueprint(app: Flask) -> Blueprint:
    """Register blueprint on api app.

    Returns:
        The registered API blueprint.
    """
    ext = app.extensions["invenio-group-collections-kcworks"]
    blueprint = ext.group_collections_resource.as_blueprint()

    return blueprint


