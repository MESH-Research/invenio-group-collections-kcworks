# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Views for Commons group collections API endpoints."""

from flask import (
    jsonify,
    current_app as app,
)
from flask_resources import (
    from_conf,
    JSONSerializer,
    JSONDeserializer,
    request_parser,
    request_body_parser,
    RequestBodyParser,
    ResponseHandler,
    Resource,
    ResourceConfig,
    route,
    resource_requestctx,
)
from invenio_access.permissions import system_identity
import marshmallow as ma
import requests
from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    MethodNotAllowed,
    NotFound,
    RequestTimeout,
    UnprocessableEntity,
    # Unauthorized,
)

from .errors import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    CommonsGroupNotFoundError,
)
from .proxies import current_group_collections_service


class GroupCollectionsResourceConfig(ResourceConfig):
    blueprint_name = "group_collections"

    url_prefix = "/group_collections"

    error_handlers = {}

    default_accept_mimetype = "application/json"

    default_content_type = "application/json"

    response_handlers = {"application/json": ResponseHandler(JSONSerializer())}

    request_body_parsers = {
        "application/json": RequestBodyParser(JSONDeserializer())
    }


class GroupCollectionsResource(Resource):

    def __init__(self, config, service):
        super().__init__(config)
        self.service = service

    error_handlers = {
        Forbidden: lambda e: (
            {"message": str(e), "status": 403},
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
                validate=ma.validate.OneOf(
                    [
                        "newest",
                        "oldest",
                        "updated-desc",
                        "updated-asc",
                    ]
                ),
                load_default="updated-desc",
            ),
            "restore_deleted": ma.fields.Boolean(load_default=False),
        },
        location="args",
    )

    def create_url_rules(self):
        """Create the URL rules for the record resource."""
        return [
            route("POST", "/", self.create),
            route("GET", "/", self.search),
            route("GET", "/<slug>", self.read),
            route("DELETE", "/", self.failed_delete),
            route("DELETE", "/<slug>", self.delete),
            route("PATCH", "/<slug>", self.change_group_ownership),
            route("PUT", "/<slug>", self.replace_group_metadata),
        ]

    def replace_group_metadata():
        raise NotImplementedError(
            "Modification of collection metadata is not supported at "
            "this endpoint. Use the main `communities` API endpoint instead."
        )

    @request_parsed_view_args
    def read(self):
        collection_slug = resource_requestctx.view_args.get("slug")
        if collection_slug:
            collection = current_group_collections_service.read(
                system_identity, collection_slug
            )
            return jsonify(collection), 200
        else:
            raise BadRequest("No collection slug provided")

    @request_parsed_args
    def search(self):
        commons_instance = resource_requestctx.args.get("commons_instance")
        commons_group_id = resource_requestctx.args.get("commons_group_id")
        page = resource_requestctx.args.get("page")
        size = resource_requestctx.args.get("size")
        sort = resource_requestctx.args.get("sort", "updated-desc")

        results = current_group_collections_service.search(
            system_identity,
            commons_instance,
            commons_group_id,
            sort=sort,
            size=size,
            page=page,
        )

        return jsonify(results.to_dict()), 200

    @request_parsed_args
    @request_data
    def create(self):
        commons_instance = resource_requestctx.data.get("commons_instance")
        commons_group_id = resource_requestctx.data.get("commons_group_id")
        restore_deleted = resource_requestctx.args.get("restore_deleted")
        collection_visibility = resource_requestctx.data.get(
            "collection_visibility"
        )

        new_collection = current_group_collections_service.create(
            system_identity,
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

    def change_group_ownership(self, collection_slug):
        # Implement the logic for handling PATCH requests to change
        # group ownership
        # request_data = request.get_json()
        # old_commons_group_id = request_data.get("old_commons_group_id")
        # new_commons_group_id = request_data.get("new_commons_group_id")
        # new_commons_group_name = request_data.get("new_commons_group_name")
        # new_commons_group_visibility = request_data.get(
        #     "new_commons_group_visibility"
        # )

        # Implement logic to modify an existing collection
        # ...

        # Construct the response
        # response_data = {
        #     "collection": collection_slug,
        #     "old_commons_group_id": old_commons_group_id,
        #     "new_commons_group_id": new_commons_group_id,
        # }

        # return jsonify(response_data), 200
        raise NotImplementedError(
            "PATCH requests to change group ownership of a collection "
            "are not yet implemented."
        )

    @request_parsed_args
    @request_parsed_view_args
    def delete(self):
        """Delete a group collection and delete the group roles.

        This is a soft delete operation. The collection is marked as deleted
        and a tombstone record is created. The group roles are also deleted.
        """
        collection_slug = resource_requestctx.view_args.get("slug")
        commons_instance = resource_requestctx.args.get("commons_instance")
        commons_group_id = resource_requestctx.args.get("commons_group_id")
        app.logger.info(
            f"Attempting to delete collection {collection_slug} for "
            f"{commons_instance} group {commons_group_id}"
        )

        if not collection_slug:
            app.logger.error("No collection slug provided. Could not delete.")
            raise BadRequest("No collection slug provided")
        elif not commons_instance:
            app.logger.error("No commons_instance provided. Could not delete.")
            raise BadRequest("No commons_instance provided")
        elif not commons_group_id:
            app.logger.error("No commons_group_id provided. Could not delete.")
            raise BadRequest("No commons_group_id provided")

        deleted_collection = current_group_collections_service.delete(
            system_identity,
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

    def failed_delete(self):
        """Error response for missing collection slug."""
        raise BadRequest("No collection slug provided")


def create_api_blueprint(app):
    """Register blueprint on api app."""

    ext = app.extensions["invenio-group-collections-kcworks"]
    blueprint = ext.group_collections_resource.as_blueprint()

    return blueprint
