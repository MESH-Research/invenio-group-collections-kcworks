# -*- coding: utf-8 -*- # # This file is part of the invenio-groups package.
# Copyright (C) 2023-2024, MESH Research.
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Views for Commons group collections API endpoints."""

# from flask import render_template
from pprint import pformat
from flask import (
    request,
    current_app as app,
    jsonify,
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
from invenio_accounts.proxies import current_datastore as accounts_datastore
from invenio_communities.errors import (
    CommunityDeletedError,
    DeletionStatusError,
    LogoSizeLimitError,
    OpenRequestsForCommunityDeletionError,
)
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.members.records.api import Member
from invenio_communities.proxies import current_communities
from io import BytesIO
import marshmallow as ma
from opensearchpy import ConflictError
from py import log
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
import os

# from invenio_groups import api

from .utils import logger
from .errors import CollectionAlreadyExistsError, CommonsGroupNotFoundError


class GroupCollectionsResourceConfig(ResourceConfig):
    blueprint_name = "group_collections"

    url_prefix = "/group_collections"

    error_handlers = {}

    default_accept_mimetype = "application/json"

    default_content_type = "application/json"

    response_handlers = {
        # Define JSON serializer for "application/json"
        "application/json": ResponseHandler(JSONSerializer())
    }

    request_body_parsers = {
        "application/json": RequestBodyParser(JSONDeserializer())
    }

    # request_data = request_body_parser(
    #     parsers=from_conf("request_body_parsers"),
    #     default_content_type=from_conf("default_content_type"),
    # )


# request_headers = request_parser(
#     {"if_match": ma.fields.Int()}, location="headers"
# )


class GroupCollectionsResource(Resource):

    def __init__(self, config, service):
        super().__init__(config)
        self.service = service

    error_handlers = {
        Forbidden: lambda e: (
            {"message": str(e.description), "status": 403},
            403,
        ),
        MethodNotAllowed: lambda e: (
            {"message": str(e.description), "status": 405},
            405,
        ),
        NotFound: lambda e: (
            {"message": str(e.description), "status": 404},
            404,
        ),
        CommonsGroupNotFoundError: lambda e: (
            {"message": str(e.description), "status": 404},
            404,
        ),
        BadRequest: lambda e: (
            {"message": str(e.description), "status": 400},
            400,
        ),
        ma.ValidationError: lambda e: (
            {"message": str(e.messages), "status": 400},
            400,
        ),
        UnprocessableEntity: lambda e: (
            {"message": str(e.description), "status": 422},
            422,
        ),
        RuntimeError: lambda e: (
            {"message": str(e.description), "status": 500},
            500,
        ),
        CollectionAlreadyExistsError: lambda e: (
            {"message": str(e.description), "status": 409},
            409,
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
        ]

    @request_parsed_view_args
    def read(self):
        collection_slug = resource_requestctx.view_args.get("slug")
        print(f"collection_slug: {collection_slug}")
        if collection_slug:
            community_list = current_communities.service.search(
                identity=system_identity, q=f"slug:{collection_slug}"
            )

            if community_list.to_dict()["hits"]["total"] == 0:
                raise NotFound(
                    f"No collection found with the slug {collection_slug}"
                )
            return jsonify(community_list.to_dict()["hits"]["hits"][0]), 200
        else:
            raise BadRequest("No collection slug provided")

    @request_parsed_args
    def search(self):
        commons_instance = resource_requestctx.args.get("commons_instance")
        commons_group_id = resource_requestctx.args.get("commons_group_id")
        page = resource_requestctx.args.get("page")
        size = resource_requestctx.args.get("size")
        sort = resource_requestctx.args.get("sort", "updated-desc")

        query_params = "+_exists_:custom_fields.kcr\:commons_instance "
        if commons_instance:
            query_params += (
                f"+custom_fields.kcr\:commons_instance:{commons_instance} "
            )
        if commons_group_id:
            query_params += (
                f"+custom_fields.kcr\:commons_group_id:{commons_group_id}"
            )
        community_list = current_communities.service.search(
            identity=system_identity,
            q=query_params,
            sort=sort,
            size=size,
            page=page,
        )

        if community_list.to_dict()["hits"]["total"] == 0:
            raise NotFound(
                "No Works collection found matching the parameters "
                f"{query_params}"
            )
        else:
            collections_data = community_list.to_dict()

        return jsonify(collections_data), 200

    @request_parsed_args
    @request_data
    def create(self):
        commons_instance = resource_requestctx.data.get("commons_instance")
        commons_group_id = resource_requestctx.data.get("commons_group_id")
        commons_group_name = resource_requestctx.data.get("commons_group_name")
        restore_deleted = resource_requestctx.args.get("restore_deleted")
        commons_group_visibility = resource_requestctx.data.get(
            "commons_group_visibility"
        )
        base_slug = commons_group_name.lower().replace(" ", "-")
        slug_incrementer = 0
        slug = base_slug
        errors = []

        instance_name = app.config["SSO_SAML_IDPS"][commons_instance]["title"]

        # make API request to commons instance to get group metadata
        commons_group_description = ""
        commons_group_url = ""
        commons_avatar_url = ""
        commons_upload_roles = []
        commons_moderate_roles = []
        api_details = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            commons_instance
        ]
        headers = {
            "Authorization": f"Bearer {os.environ[api_details['token_name']]}"
        }
        try:
            meta_response = requests.get(
                api_details["url"].format(id=commons_group_id),
                headers=headers,
                timeout=15,
            )
        except requests.exceptions.Timeout:
            raise RequestTimeout(
                "Request to Commons instance for group metadata timed out"
            )
        except requests.exceptions.ConnectionError:
            raise requests.exceptions.ConnectionError(
                "Could not connect to "
                "Commons instance to fetch group metadata"
            )
        if meta_response.status_code == 200:
            content = meta_response.json()
            commons_group_description = content["description"]
            commons_group_url = content["url"]
            commons_avatar_url = content["avatar"]
            if commons_avatar_url == api_details.get("default_avatar"):
                commons_avatar_url = None
            commons_upload_roles = content["upload_roles"]
            commons_moderate_roles = content["moderate_roles"]
        elif meta_response.status_code == 404:
            logger.error(
                f"Failed to get metadata for group {commons_group_id} on "
                f"{instance_name}"
            )
            logger.error(f"Response: {meta_response.text}")
            logger.error(headers)
            raise CommonsGroupNotFoundError(
                f"No such group {commons_group_id} could be found "
                f"on {instance_name}"
            )
        else:
            logger.error(
                f"Failed to get metadata for group {commons_group_id} on "
                f"{instance_name}"
            )
            logger.error(f"Response: {meta_response.text}")
            logger.error(headers)
            raise UnprocessableEntity(
                f"Something went wrong requesting group {commons_group_id} "
                f"on {instance_name}"
            )

        # create roles for the new collection's group members
        remote_roles = list(
            set([*commons_upload_roles, *commons_moderate_roles])
        )
        for role in remote_roles:
            group_name = f"{commons_instance}|{commons_group_id}|{role}"
            my_group_role = accounts_datastore.find_or_create_role(
                name=group_name
            )
            accounts_datastore.commit()

            if my_group_role is not None:
                assert my_group_role.name == group_name
                logger.info(
                    f'Role "{group_name}" created or retrieved successfully.'
                )
            else:
                raise RuntimeError(f'Role "{group_name}" not created.')

        # create the new collection
        new_record = None
        data = {
            "access": {
                "visibility": "restricted",
                "member_policy": "closed",
                "record_policy": "closed",
            },
            "slug": slug,
            "metadata": {
                "title": f"{commons_group_name}",
                "description": f"A collection managed by the "
                f"{commons_group_name} group of {instance_name}",
                "curation_policy": "",
                "page": f"This"
                " is a collection of works curated by the "
                f"{commons_group_name} group of {instance_name}",
                "website": commons_group_url,
                "organizations": [
                    {
                        "name": commons_group_name,
                    },
                    {"name": instance_name},
                ],
            },
            "custom_fields": {
                "kcr:commons_instance": commons_instance,
                "kcr:commons_group_id": commons_group_id,
                "kcr:commons_group_name": commons_group_name,
                "kcr:commons_group_description": commons_group_description,  # noqa: E501
                "kcr:commons_group_visibility": commons_group_visibility,  # noqa: E501
            },
        }

        while not new_record:
            try:
                new_record_result = current_communities.service.create(
                    identity=system_identity, data=data
                )
                logger.info(f"New record created successfully: {new_record}")
                new_record = new_record_result
                if not new_record_result:
                    raise RuntimeError("Failed to create new collection")
            except ma.ValidationError as e:
                # group with slug already exists
                logger.error(f"Validation error: {e}")
                if "A community with this identifier already exists" in str(e):
                    community_list = current_communities.service.search(
                        identity=system_identity, q=f"slug:{slug}"
                    )
                    if community_list.to_dict()["hits"]["total"] < 1:
                        msg = f"Collection for {instance_name} group {commons_group_id} seems to have been deleted previously and has not been restored. Continuing with a new url slug."  # noqa: E501
                        logger.error(msg)
                        # raise DeletionStatusError(False, msg)
                        # TODO: provide the option of restoring a deleted
                        # collection here? `restore_deleted` query param is
                        # in place

                        if restore_deleted:
                            raise NotImplementedError(
                                "Restore deleted collection not yet implemented"
                            )
                        else:
                            slug_incrementer += 1
                            slug = f"{base_slug}-{str(slug_incrementer)}"
                            data["slug"] = slug
                    elif (
                        community_list.to_dict()["hits"][0]["custom_fields"][
                            "kcr:commons_group_id"
                        ]
                        == commons_group_id
                    ):
                        raise CollectionAlreadyExistsError(
                            f"Collection for {instance_name} "
                            f"group {commons_group_id} already exists"
                        )
                    else:
                        slug_incrementer += 1
                        slug = f"{base_slug}-{str(slug_incrementer)}"
                        data["slug"] = slug
                else:
                    raise UnprocessableEntity(str(e))

        # assign admins as members of the new collection
        try:
            manage_payload = [{"type": "group", "id": "administrator"}]
            manage_members = current_communities.service.members.add(
                system_identity,
                new_record["id"],
                data={"members": manage_payload, "role": "administrator"},
            )
            logger.error(f"Manage members: {pformat(manage_members)}")
        except AlreadyMemberError:
            logger.error("admin role is already a manager")

        # assign the group roles as members of the new collection
        for remote_role in remote_roles:
            try:
                works_role = "reader"
                if remote_role in commons_upload_roles:
                    works_role = "curator"
                elif remote_role in commons_moderate_roles:
                    works_role = "administrator"  # or "owner"?
                payload = [
                    {
                        "type": "group",
                        "id": f"{commons_instance}|{commons_group_id}"
                        f"|{remote_role}",
                    }
                ]
                member = current_communities.service.members.add(
                    system_identity,
                    new_record["id"],
                    data={"members": payload, "role": works_role},
                )
                assert member
            except AlreadyMemberError:
                logger.error(
                    f"{remote_role} role was was already a group member"
                )
        logger.error(pformat(new_record))

        # download the group avatar and upload it to the Invenio instance
        if commons_avatar_url:
            try:
                avatar_response = requests.get(commons_avatar_url, timeout=15)
            except requests.exceptions.Timeout:
                logger.error(
                    "Request to Commons instance for group avatar timed out"
                )
            except requests.exceptions.ConnectionError:
                logger.error(
                    "Could not connect to "
                    "Commons instance to fetch group avatar"
                )
            if avatar_response.status_code == 200:
                try:
                    logo_result = current_communities.service.update_logo(
                        system_identity,
                        new_record["id"],
                        stream=BytesIO(avatar_response.content),
                    )
                    if logo_result is not None:
                        logger.info("Logo uploaded successfully.")
                    else:
                        logger.error("Logo upload failed silently in Invenio.")
                except Exception as e:
                    logger.error(f"Logo upload failed: {e}")
                    errors.append(f"Logo upload failed in Invenio: {e}")
            elif avatar_response.status_code in [400, 405, 406, 412, 413]:
                logger.error(
                    "Request was not accepted when trying to access "
                    f"the provided avatar at {commons_avatar_url}"
                )
                logger.error(f"Response: {avatar_response.text}")
            elif avatar_response.status_code in [401, 403, 407]:
                logger.error(
                    "Access the provided avatar was not allowed "
                    f"at {commons_avatar_url}"
                )
                logger.error(f"Response: {avatar_response.text}")
            elif avatar_response.status_code in [404, 410]:
                logger.error(
                    f"Provided avatar was not found at {commons_avatar_url}"
                )
                logger.error(f"Response: {avatar_response.text}")
            elif avatar_response.status_code == 403:
                logger.error(
                    "Access to the provided avatar was forbidden"
                    f" at {commons_avatar_url}"
                )
                logger.error(f"Response: {avatar_response.text}")
            elif avatar_response.status_code in [500, 502, 503, 504, 509, 511]:
                logger.error(
                    f"Connection failed when trying to access the "
                    f"provided avatar at {commons_avatar_url}"
                )
                logger.error(f"Response: {avatar_response.text}")

        # Construct the response
        response_data = {
            "commons_group_id": commons_group_id,
            "collection": slug,
        }

        return jsonify(response_data), 201

    def change_group_ownership(self, collection_slug):
        # Implement the logic for handling PATCH requests to change group ownership
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
        """Delete a group collection and delete the group roles."""
        collection_slug = resource_requestctx.view_args.get("slug")
        commons_instance = resource_requestctx.args.get("commons_instance")
        commons_group_id = resource_requestctx.args.get("commons_group_id")
        logger.info(
            f"Attempting to delete collection {collection_slug} for "
            f"{commons_instance} group {commons_group_id}"
        )

        if not collection_slug:
            logger.error("No collection slug provided. Could not delete.")
            raise BadRequest("No collection slug provided")
        elif not commons_instance:
            logger.error("No commons_instance provided. Could not delete.")
            raise BadRequest("No commons_instance provided")
        elif not commons_group_id:
            logger.error("No commons_group_id provided. Could not delete.")
            raise BadRequest("No commons_group_id provided")

        try:
            collection_record = current_communities.service.read(
                system_identity, collection_slug
            )
            if not collection_record:
                msg = f"No collection found with the slug {collection_slug}. Could not delete."  # noqa: E501
                logger.error(msg)
                raise NotFound(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_instance")
                != commons_instance
            ):
                msg = f"Collection {collection_slug} does not belong to {commons_instance}. Could not delete."  # noqa: E501
                logger.error(msg)
                raise Forbidden(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_group_id")
                != commons_group_id
            ):
                msg = f"Collection {collection_slug} does not belong to group {commons_group_id}. Could not delete."  # noqa: E501
                logger.error(msg)
                raise Forbidden(msg)

            deleted = current_communities.service.delete(
                system_identity, collection_slug
            )
            if deleted:
                logger.info(
                    f"Collection {collection_slug} belonging to "
                    f"{commons_instance} group {commons_group_id}"
                    "deleted successfully."
                )
            else:
                msg = f"Failed to delete collection {collection_slug} belonging to {commons_instance} group {commons_group_id}"  # noqa: E501
                logger.error(msg)
                raise RuntimeError(msg)
        except (DeletionStatusError, CommunityDeletedError) as e:
            msg = f"Collection has already been deleted: {str(e)}"
            logger.error(msg)
            raise UnprocessableEntity(msg)
        except OpenRequestsForCommunityDeletionError as oe:
            msg = "Cannot delete a collection with open" f"requests: {str(oe)}"
            logger.error(msg)
            raise UnprocessableEntity(msg)

        # Return appropriate response status
        return (
            f"Successfully deleted collection {collection_slug} "
            f"for {commons_instance} group {commons_group_id}",
            204,
        )

    def failed_delete(self):
        """Error response for missing collection slug."""
        raise BadRequest("No collection slug provided")


def create_api_blueprint(app):
    """Register blueprint on api app."""

    ext = app.extensions["invenio-groups"]
    blueprint = ext.group_collections_resource.as_blueprint()

    return blueprint
