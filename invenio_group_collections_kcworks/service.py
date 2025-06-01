# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

from flask import current_app as app
from flask_principal import Identity
from invenio_accounts.proxies import current_datastore as accounts_datastore
from invenio_access.permissions import system_identity
from invenio_communities.communities.services.results import (
    CommunityItem,
    CommunityListResult,
)
from invenio_communities.errors import (
    CommunityDeletedError,
    DeletionStatusError,
    OpenRequestsForCommunityDeletionError,
)
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.proxies import current_communities
from invenio_records_resources.services.records.service import RecordService
from invenio_search.proxies import current_search_client
from io import BytesIO
import marshmallow as ma
import os
from pprint import pformat
import requests
from typing import Optional
from werkzeug.exceptions import (
    Forbidden,
    NotFound,
    RequestTimeout,
    UnprocessableEntity,
    # Unauthorized,
)

from .errors import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    CollectionNotCreatedError,
    CommonsGroupNotFoundError,
    RoleNotCreatedError,
)
from .utils import (
    make_base_group_slug,
    convert_remote_roles,
    add_user_to_community,
)


class GroupCollectionsService(RecordService):
    """Service for managing group collections."""

    def __init__(self, config: dict = {}, **kwargs):
        """Constructor."""
        super().__init__(config=config, **kwargs)

    def update_avatar(self, commons_avatar_url: str, community_record_id: str) -> bool:
        """Update the avatar of a community in Invenio from the provided url.

        params:
            commons_avatar_url: The URL of the avatar to fetch.
            community_record_id: The ID of the community to update.

        returns:
            True if the avatar was updated successfully, otherwise False.
        """

        success = False
        try:
            avatar_response = requests.get(commons_avatar_url, timeout=15)
        except requests.exceptions.Timeout:
            app.logger.error("Request to Commons instance for group avatar timed out")
        except requests.exceptions.ConnectionError:
            app.logger.error(
                "Could not connect to " "Commons instance to fetch group avatar"
            )
        if avatar_response.status_code == 200:
            try:
                logo_result = current_communities.service.update_logo(
                    system_identity,
                    community_record_id,
                    stream=BytesIO(avatar_response.content),
                )
                if logo_result is not None:
                    app.logger.info("Logo uploaded successfully.")
                    success = True
                else:
                    app.logger.error("Logo upload failed silently in Invenio.")
            except Exception as e:
                app.logger.error(f"Logo upload failed: {e}")
        elif avatar_response.status_code in [400, 405, 406, 412, 413]:
            app.logger.error(
                "Request was not accepted when trying to access "
                f"the provided avatar at {commons_avatar_url}"
            )
            app.logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code in [401, 403, 407]:
            app.logger.error(
                f"Access the provided avatar was not allowed at {commons_avatar_url}"
            )
            app.logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code in [404, 410]:
            app.logger.error(f"Provided avatar was not found at {commons_avatar_url}")
            app.logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code == 403:
            app.logger.error(
                "Access to the provided avatar was forbidden"
                f" at {commons_avatar_url}"
            )
            app.logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code in [500, 502, 503, 504, 509, 511]:
            app.logger.error(
                f"Connection failed when trying to access the "
                f"provided avatar at {commons_avatar_url}"
            )
            app.logger.error(f"Response: {avatar_response.text}")

        return success

    def read(
        self,
        identity: Identity,
        slug: str,
    ) -> CommunityItem:
        """Read a collection (community) by its slug.

        raises:
            CollectionNotFoundError: If no collection is found in Invenio with
            the given slug.

        returns:
            A CommunityItem object representing the collection.
        """

        community_list = current_communities.service.search(
            identity=identity, q=f"slug:{slug}"
        )

        if community_list.total == 0:
            raise CollectionNotFoundError(f"No collection found with the slug {slug}")
        result = next(community_list.hits)

        return result

    def search(
        self,
        identity: Identity,
        commons_instance: str,
        commons_group_id: Optional[str] = None,
        sort: Optional[str] = "updated-desc",
        size: Optional[int] = 10,
        page: Optional[int] = 1,
    ) -> CommunityListResult:
        """Search collections (communities) by Commons instance and group ID.

        params:
            identity: The Identity of the user making the request. [required]
            commons_instance: The name of the Commons instance. [required]
            commons_group_id: The ID of the group on the Commons instance.
            sort: The sort order for the results.
            size: The number of results to return.
            page: The page number of the results to return.

        Although commons_instance and commons_group_id are optional, at least
        one of them must be provided.

        If only the commons instance is provided, all collections belonging to
        that instance will be returned. If the group ID is also provided, all
        collections belonging to that group will be returned.

        raises:
            CollectionNotFoundError: If no collections are found matching
                the parameters.
            UnprocessableEntityError: If the query parameters are invalid.

        returns:
            Returns a CommunityListResult object.
        """
        query_params = "+_exists_:custom_fields.kcr\:commons_instance "  # noqa
        if commons_instance:
            query_params += (
                f"+custom_fields.kcr\:commons_instance:"  # noqa: W605
                f"{commons_instance} "
            )
        if commons_group_id:
            query_params += (
                f"+custom_fields.kcr\:commons_group_id:"  # noqa: W605
                f"{commons_group_id}"
            )
        community_list = current_communities.service.search(
            identity=identity,
            params={
                "q": query_params,
                "sort": sort,
                "size": int(size) if size else 10,
                "page": int(page) if page else 1,
            },
        )

        if community_list.to_dict()["hits"]["total"] == 0:
            raise CollectionNotFoundError(
                f"No Works collection found matching the parameters {query_params}"
            )

        return community_list

    def create(
        self,
        identity: Identity,
        commons_group_id: str,
        commons_instance: str,
        restore_deleted: bool = False,
        collection_visibility: str = "public",
        **kwargs,
    ) -> CommunityItem:
        """Create a in Invenio collection (community) belonging to a KC group.

        Unlike most Invenio services, this "create" method does not take a
        `data` parameter. Instead the method fetches the necessary data from
        the Commons instance and constructs the collection metadata from that
        data.

        Note that group collections are created with the administrative user
        as the collection owner. The group's admins are added as managers of
        the collection.

        params:
            identity: The identity of the user creating the collection.
            commons_group_id: The ID of the group on the Commons instance.
            commons_instance: The name of the Commons instance.
            restore_deleted: If True, the collection will be restored if it
                was previously deleted. If False, a new collection will be
                created with a new slug. [default: False]
            collection_visibility: The visibility of the collection. May be
                either "public" or "restricted" [default: "public"]
            **kwargs: Additional keyword arguments.

        raises:
            CommonsGroupNotFoundError: If the group is not found on the
                Commons instance.
            CollectionAlreadyExistsError: If a collection for the group
                already exists and has not been deleted.
            CollectionNotCreatedError: If the collection could not be created
                for some other reason.
            RequestTimeout: If the request to the Commons instance api
                endpoint times out.

        returns:
            The created collection record.
        """
        instance_name = app.config["SSO_SAML_IDPS"][commons_instance]["title"]
        # make API request to commons instance to get group metadata
        commons_group_name = ""
        commons_group_description = ""
        commons_group_url = ""
        commons_avatar_url = ""
        commons_upload_roles = []
        commons_moderate_roles = []
        api_details = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            commons_instance
        ]
        headers = {"Authorization": f"Bearer {os.environ[api_details['token_name']]}"}
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
                "Could not connect to Commons instance to fetch group metadata"
            )
        if meta_response.status_code == 200:
            content = meta_response.json()
            app.logger.error(f"Group metadata: {pformat(content)}")
            if not content or commons_group_id not in [
                content["id"],
                str(content["id"]),
            ]:
                raise CommonsGroupNotFoundError(
                    f"No such group {commons_group_id} could be found "
                    f"on {instance_name}"
                )
            else:
                commons_group_name = content["name"]
                commons_group_description = content["description"]
                commons_group_visibility = content["visibility"]
                commons_group_url = content["url"]
                commons_avatar_url = content["avatar"]
                if commons_avatar_url == api_details.get("default_avatar"):
                    commons_avatar_url = None
                commons_upload_roles = content["upload_roles"]
                commons_moderate_roles = content["moderate_roles"]

                base_slug = make_base_group_slug(commons_group_name)
                slug_incrementer = 0
                slug = base_slug
                app.logger.error(f"Base slug: {slug}")

        elif meta_response.status_code == 404:
            app.logger.error(
                f"Failed to get metadata for group {commons_group_id} on "
                f"{instance_name}"
            )
            app.logger.error(f"Response: {meta_response.text}")
            app.logger.error(headers)
            raise CommonsGroupNotFoundError(
                f"No such group {commons_group_id} could be found "
                f"on {instance_name}"
            )
        else:
            app.logger.error(
                f"Failed to get metadata for group {commons_group_id} on "
                f"{instance_name}"
            )
            app.logger.error(f"Response: {meta_response.text}")
            app.logger.error(headers)
            raise UnprocessableEntity(
                f"Something went wrong requesting group {commons_group_id} "
                f"on {instance_name}"
            )

        # create roles for the new collection's group members
        invenio_roles = convert_remote_roles(
            f"{commons_instance}---{commons_group_id}",
            commons_moderate_roles,
            commons_upload_roles,
        )
        print("GroupCollectionService creating roles")
        print(invenio_roles)
        app.logger.debug("GroupCollectionService creating roles")
        app.logger.debug(invenio_roles)
        for key, value in invenio_roles.items():
            for remote_role in value:
                my_group_role = accounts_datastore.find_or_create_role(name=remote_role)
                accounts_datastore.commit()

                if my_group_role is None:
                    raise RoleNotCreatedError(f'Role "{remote_role}" not created.')

        # create the new collection
        new_record = None
        data = {
            "access": {
                "visibility": collection_visibility,
                "member_policy": "closed",
                "record_policy": "closed",
                "review_policy": "closed",
            },
            "slug": slug,
            "metadata": {
                "title": f"{commons_group_name}",
                "description": (
                    f"A collection managed by "
                    f"{commons_group_name}, a {instance_name} group"
                ),
                "curation_policy": "",
                "page": (
                    f"This"
                    " is a collection of works curated by "
                    f"{commons_group_name}, a {instance_name} group"
                ),
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
                "kcr:commons_group_description": (
                    commons_group_description
                ),  # noqa: E501
                "kcr:commons_group_visibility": commons_group_visibility,  # noqa: E501
            },
        }
        app.logger.debug(f"New collection data: {pformat(data)}")

        while not new_record:
            try:
                new_record_result = current_communities.service.create(
                    identity=system_identity, data=data
                )
                app.logger.info(f"New record created successfully: {new_record}")
                new_record = new_record_result
                if not new_record_result:
                    raise CollectionNotCreatedError("Failed to create new collection")
            except ma.ValidationError as e:
                # group with slug already exists
                app.logger.error(f"Validation error: {e}")
                if "A community with this identifier already exists" in str(e):
                    community_list = current_communities.service.search(
                        identity=system_identity, q=f"slug:{slug}"
                    )
                    if community_list.total < 1:
                        msg = f"Collection for {instance_name} group {commons_group_id} seems to have been deleted previously and has not been restored. Continuing with a new url slug."  # noqa: E501
                        app.logger.error(msg)
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
                        community_list.total == 1
                        and community_list.to_dict()["hits"]["hits"][0][
                            "custom_fields"
                        ]["kcr:commons_group_id"]
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
                    raise CollectionNotCreatedError(str(e))

        # assign the configured administrative user as owner of the
        # new collection
        # if no account is configured, assign the first administrative user
        # NOTE: this allows the admin to manage the collection in the UI
        # is also ensures that the collection will be marked as "verified"
        admin_email = app.config.get("GROUP_COLLECTIONS_ADMIN_EMAIL")
        admin_by_email = accounts_datastore.get_user_by_email(admin_email)
        if admin_by_email:
            admin_id = admin_by_email.id
        else:
            admin_role = accounts_datastore.find_role_by_id("admin")
            admin_role_holders = [
                u for u in accounts_datastore.find_role(admin_role.name).users
            ]
            assert len(admin_role_holders) > 0  # should be at least one admin
            admin_id = admin_role_holders[0].id
        member = current_communities.service.members.add(
            system_identity,
            new_record["id"],
            data={
                "members": [{"type": "user", "id": str(admin_id)}],
                "role": "owner",
            },
        )

        # assign admins as members of the new collection
        try:
            manage_payload = [{"type": "group", "id": "admin"}]
            manage_members = current_communities.service.members.add(
                system_identity,
                new_record["id"],
                data={"members": manage_payload, "role": "owner"},
            )
            app.logger.error(f"Admin owner members: {pformat(manage_members)}")
        except AlreadyMemberError:
            app.logger.error("adminstrator role is already an owner")

        # assign the group roles as members of the new collection
        for coll_perm, remote_roles in invenio_roles.items():
            for role in remote_roles:
                payload = [
                    {
                        "type": "group",
                        "id": role,
                    }
                ]
                try:
                    member = current_communities.service.members.add(
                        system_identity,
                        new_record["id"],
                        data={
                            "members": payload,
                            "role": coll_perm,
                        },
                    )
                    assert member
                except AlreadyMemberError:
                    app.logger.error(f"{role} role was was already a group member")
        app.logger.error(pformat(new_record))

        # download the group avatar and upload it to the Invenio instance
        if commons_avatar_url and "mystery-group.png" not in commons_avatar_url:
            self.update_avatar(commons_avatar_url, new_record["id"])

        # current_communities.service.record_cls.index.refresh()

        return new_record

    def delete(
        self,
        identity: Identity,
        collection_slug: str,
        commons_instance: str,
        commons_group_id: str,
    ) -> CommunityItem:
        """Delete the collection belonging to the given Commons group.

        This is a soft delete. The collection will be marked as deleted but
        a tombstone record will be retained and can still be retrieved from
        the database.

        If the collection is successfully deleted, the method will also delete
        the roles associated with the collection.

        params:
            identity: The identity of the user making the request.
            collection_slug: The slug of the collection to delete.
            commons_instance: The name of the Commons instance.
            commons_group_id: The ID of the group on the Commons instance.

        returns:
            A CommunityItem object representing the deleted collection.
        """

        try:
            collection_record = current_communities.service.read(
                system_identity, collection_slug
            )
            if not collection_record:
                msg = f"No collection found with the slug {collection_slug}. Could not delete."  # noqa: E501
                app.logger.error(msg)
                raise NotFound(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_instance")
                != commons_instance
            ):
                msg = f"Collection {collection_slug} does not belong to {commons_instance}. Could not delete."  # noqa: E501
                app.logger.error(msg)
                raise Forbidden(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_group_id")
                != commons_group_id
            ):
                msg = f"Collection {collection_slug} does not belong to group {commons_group_id}. Could not delete."  # noqa: E501
                app.logger.error(msg)
                raise Forbidden(msg)

            deleted = current_communities.service.delete(
                system_identity, collection_slug
            )
            if deleted:
                app.logger.info(
                    f"Collection {collection_slug} belonging to "
                    f"{commons_instance} group {commons_group_id}"
                    "deleted successfully."
                )
            else:
                msg = f"Failed to delete collection {collection_slug} belonging to {commons_instance} group {commons_group_id}"  # noqa: E501
                app.logger.error(msg)
                raise RuntimeError(msg)
        except (DeletionStatusError, CommunityDeletedError) as e:
            msg = f"Collection has already been deleted: {str(e)}"
            app.logger.error(msg)
            raise UnprocessableEntity(msg)
        except OpenRequestsForCommunityDeletionError as oe:
            msg = "Cannot delete a collection with open" f"requests: {str(oe)}"
            app.logger.error(msg)
            raise UnprocessableEntity(msg)

        # TODO: Is this manual refresh necessary?
        # This manual refresh resulted in a 404 error for the index
        # Community.index.refresh()

        return deleted

    def disown(
        self,
        identity: Identity,
        collection_id: str,
        collection_slug: str,
        remote_group_id: str,
        remote_instance_name: str,
    ) -> CommunityItem:
        """Remove all connections between the remote group and the collection.

        This method will remove all role-based members of the collection that
        are associated with the remote group. It will also remove the remote
        group's metadata from the collection.

        All users who were formerly members of the remote group by virtue of
        their roles will be re-added as individual members of the collection
        with permission levels based on their former roles.

        The group roles themselves (that were used to assign group memberships
        in the collection) will not be deleted. This is because the group
        itself may still exist and may create a new collection in the future.
        They will only be deleted when the group itself is deleted.

        params:
            identity: The identity of the user making the request.
            collection_id: The ID of the collection to disown.
            collection_slug: The slug of the collection to disown.
            remote_group_id: The ID of the group on the remote Commons
            instance.
            remote_instance_name: The name of the remote Commons instance.

        returns:
            A CommunityItem object representing the disowned collection. This
            should have no group-based members linked to the remote group, and
            the remote group's metadata should be removed from its
            custom_fields.
        """
        app.logger.info(
            f"GroupCollectionsService: Disowning collection "
            f"{collection_slug} from {remote_instance_name} "
            f"group {remote_group_id}"
        )
        model_class = current_communities.service.members.record_cls.model_cls
        query = model_class.query.filter(
            model_class.group_id.contains(f"{remote_instance_name}---{remote_group_id}")
        )
        group_members = [(g.group_id, g.role) for g in query.all()]
        app.logger.info(f"Group members to remove: {group_members}")

        individual_memberships = []
        failures = []
        for member_role in group_members:
            app.logger.info(f"Group member to remove: {member_role}")
            individuals = [
                u for u in accounts_datastore.find_role(member_role[0]).users
            ]
            app.logger.info(f"Individuals: {pformat(individuals)}")

            for member in individuals:
                # assign member to the group collection community
                # directly with a community role based on their former
                # group role
                add_result = add_user_to_community(
                    member.id, member_role[1], int(collection_id)
                )
                if add_result:
                    individual_memberships.append((member.id, member_role[1]))
                    app.logger.info(f"Member {member.id} reassigned successfully.")
                else:
                    failures.append(member)

            members = current_communities.service.members.record_cls.get_members(
                collection_id,
                members=[{"type": "group", "id": member_role[0]}],
            )
            app.logger.info(f"Members to remove: {pformat(members)}")
            if members:
                current_communities.service.members.delete(
                    system_identity,
                    collection_id,
                    data={"members": [{"id": member_role[0], "type": "group"}]},
                )

        if failures:
            raise RuntimeError("Failed to reassign all members to the collection.")

        # remove the remote group's metadata from the collection
        collection_record = current_communities.service.read(
            system_identity, collection_id
        )
        new_data = collection_record.to_dict()
        removals = {
            "kcr:commons_instance": "",
            "kcr:commons_group_id": "",
            "kcr:commons_group_name": "",
            "kcr:commons_group_description": "",
            "kcr:commons_group_visibility": "",
        }
        new_data["custom_fields"].update(removals)
        new_record = current_communities.service.update(
            system_identity, collection_id, data=new_data
        )

        current_search_client.indices.refresh(index="*communities*")

        return new_record
