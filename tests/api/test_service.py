#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for the invenio-group-collections-kcworks service."""

# from pprint import pprint
import pytest
from invenio_access.models import ActionRoles
from invenio_access.permissions import any_user, authenticated_user, system_identity
from invenio_access.utils import get_identity
from invenio_accounts import current_accounts
from invenio_communities.communities.records.api import Community
from invenio_communities.proxies import current_communities
from invenio_group_collections_kcworks.errors import (
    CollectionAlreadyExistsError,
    CommonsGroupNotFoundError,
)
from invenio_group_collections_kcworks.permissions import (
    group_collections_write_action,
)
from invenio_group_collections_kcworks.proxies import (
    current_group_collections,
)
from invenio_group_collections_kcworks.proxies import (
    current_group_collections_service as current_collections,
)
from invenio_group_collections_kcworks.service import (
    GroupCollectionsService,
    remote_to_invenio_visibility,
)

# Remote Profiles "group not found" body (create path treats this as missing).
_NOT_FOUND_REMOTE = {
    "id": 0,
    "name": None,
    "url": "",
    "visibility": None,
    "description": None,
    "avatar": False,
    "groupblog": "",
    "upload_roles": ["member", "moderator", "administrator"],
    "moderate_roles": ["moderator", "administrator"],
}

_AVATAR_URL = (
    "https://hcommons-dev.org/app/plugins/buddypress/bp-core/"
    "images/mystery-group.png"
)

# Detailed remote group used by create→mapping assertions in this module.
_INKLINGS_GROUP_ID = "1004290"
_INKLINGS_REMOTE = {
    "id": _INKLINGS_GROUP_ID,
    "name": "The Inklings",
    "url": "https://hcommons-dev.org/groups/the-inklings/",
    "visibility": "public",
    "description": (
        "For scholars interested in J.R.R. Tolkien, C. S. Lewis, "
        "Charles Williams, and other writers associated with the "
        "Inklings."
    ),
    "avatar": _AVATAR_URL,
    "groupblog": "",
    "upload_roles": ["member", "moderator", "administrator"],
    "moderate_roles": ["moderator", "administrator"],
}
_INKLINGS_EXPECTED = {
    "slug": "the-inklings",
    "metadata": {
        "title": "The Inklings",
        "description": (
            "A collection managed by The Inklings, a Knowledge Commons group"
        ),
        "curation_policy": "",
        "page": (
            "This is a collection of works curated by The Inklings, "
            "a Knowledge Commons group"
        ),
        "website": "https://hcommons-dev.org/groups/the-inklings/",
        "organizations": [
            {"name": "The Inklings"},
            {"name": "Knowledge Commons"},
        ],
    },
    "access": {
        "visibility": "public",
        "members_visibility": "public",
        "member_policy": "closed",
        "record_submission_policy": "closed",
        "review_policy": "closed",
    },
    "custom_fields": {
        "kcr:commons_instance": "knowledgeCommons",
        "kcr:commons_group_id": _INKLINGS_GROUP_ID,
        "kcr:commons_group_name": "The Inklings",
        "kcr:commons_group_description": _INKLINGS_REMOTE["description"],
        "kcr:commons_group_visibility": "public",
    },
    "deletion_status": {
        "is_deleted": False,
        "status": "P",
    },
    "children": {"allow": False},
}


def _mock_profiles_group(app, requests_mock, group_id: str, payload: dict) -> None:
    """Stub Profiles group GET + avatar fetch for create/associate/transfer."""
    update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
        "knowledgeCommons"
    ]["url"]
    requests_mock.get(update_url + group_id, json=payload)
    requests_mock.get(_AVATAR_URL, status_code=404)


def _linked_collection(minimal_community_factory, *, group_id: str, slug: str):
    """Seed an already-linked group collection via shared minimal_community_factory.

    Returns:
        The community service item for the seeded collection.
    """
    return minimal_community_factory(
        slug=slug,
        metadata={"title": slug.replace("-", " ").title()},
        custom_fields={
            "kcr:commons_instance": "knowledgeCommons",
            "kcr:commons_group_id": group_id,
            "kcr:commons_group_name": slug,
            "kcr:commons_group_description": "",
            "kcr:commons_group_visibility": "public",
        },
    )


@pytest.fixture
def group_collections_writer(UserFixture, app, db):
    """Non-admin user with group-collections-write capability only.

    Returns:
        The created user fixture with the write capability role.
    """
    role = current_accounts.datastore.find_or_create_role(
        name="group-collections-write"
    )
    current_accounts.datastore.commit()
    if not any(
        existing.role_id == role.id
        for existing in ActionRoles.query_by_action(
            group_collections_write_action
        ).all()
    ):
        db.session.add(
            ActionRoles.create(action=group_collections_write_action, role=role)
        )
        db.session.commit()
    u = UserFixture(
        email="svc-group-collections-assoc@example.org",
        password="password",
    )
    u.create(app, db)
    current_accounts.datastore.add_role_to_user(u.user, role)
    current_accounts.datastore.commit()
    return u


def test_remote_to_invenio_visibility_public():
    """remote_to_invenio_visibility maps 'public' to 'public'."""
    assert remote_to_invenio_visibility("public") == "public"


def test_remote_to_invenio_visibility_private():
    """remote_to_invenio_visibility maps 'private' to 'restricted'."""
    assert remote_to_invenio_visibility("private") == "restricted"


def test_remote_to_invenio_visibility_hidden():
    """remote_to_invenio_visibility maps 'hidden' to 'restricted'."""
    assert remote_to_invenio_visibility("hidden") == "restricted"


def test_remote_to_invenio_visibility_unknown_fallback():
    """remote_to_invenio_visibility falls back to 'public' for unknown values."""
    assert remote_to_invenio_visibility("unknown") == "public"
    assert remote_to_invenio_visibility("") == "public"


def test_collections_service_init(app):
    """Test service initialization."""
    with app.app_context():
        ext = current_group_collections
        collections_service = ext.collections_service
        assert collections_service
        assert isinstance(collections_service, GroupCollectionsService)


def test_collections_service_create(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    admin,
):
    """Test service creation."""
    with app.app_context():
        _mock_profiles_group(
            app, requests_mock, _INKLINGS_GROUP_ID, _INKLINGS_REMOTE
        )
        assert admin.user

        actual = current_collections.create(
            system_identity,
            _INKLINGS_GROUP_ID,
            "knowledgeCommons",
        )
        actual_data = actual.to_dict()
        for key, value in _INKLINGS_EXPECTED.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    assert actual_data[key][nested_key] == nested_value
            else:
                assert actual_data[key] == value
        assert actual_data["revision_id"] >= 2

        actual_slug = actual.data["slug"]
        Community.index.refresh()
        community_list = current_communities.service.search(
            identity=system_identity, q=f"slug:{actual_slug}"
        ).to_dict()
        assert len(community_list["hits"]["hits"]) == 1

        read_data = community_list["hits"]["hits"][0]
        for key, value in _INKLINGS_EXPECTED.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    assert read_data[key][nested_key] == nested_value
            else:
                assert read_data[key] == value


def test_collections_service_create_not_found(
    app, db, requests_mock, search_clear, location
):
    """Test service creation when requested group cannot be found."""
    with app.app_context():
        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ]["url"]
        requests_mock.get(
            update_url + "1004290111",
            status_code=200,
            headers={"Content-Type": "application/json"},
            json=_NOT_FOUND_REMOTE,
        )

        with pytest.raises(CommonsGroupNotFoundError):
            current_collections.create(
                system_identity, "1004290111", "knowledgeCommons"
            )


def test_collections_service_create_already_deleted(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
    admin,
):
    """Create increments the slug when a soft-deleted collection already exists."""
    with app.app_context():
        _mock_profiles_group(
            app, requests_mock, _INKLINGS_GROUP_ID, _INKLINGS_REMOTE
        )
        assert admin.user

        existing = _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        Community.index.refresh()
        current_communities.service.delete(system_identity, existing.id)
        Community.index.refresh()

        actual = current_collections.create(
            system_identity,
            _INKLINGS_GROUP_ID,
            "knowledgeCommons",
        )
        actual_data = actual.to_dict()
        # slug is incremented because of soft-deleted community
        expected = {**_INKLINGS_EXPECTED, "slug": "the-inklings-1"}
        for key, value in expected.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    assert actual_data[key][nested_key] == nested_value
            else:
                assert actual_data[key] == value


def test_collections_service_create_already_exists(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
    admin,
):
    """Create raises when an active collection already exists for the group."""
    with app.app_context():
        _mock_profiles_group(
            app, requests_mock, _INKLINGS_GROUP_ID, _INKLINGS_REMOTE
        )
        _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        Community.index.refresh()

        with pytest.raises(CollectionAlreadyExistsError):
            current_collections.create(
                system_identity,
                _INKLINGS_GROUP_ID,
                "knowledgeCommons",
            )


def _api_group(
    group_id: str,
    name: str,
    *,
    slug: str | None = None,
) -> dict:
    """Build a Commons group metadata API payload for requests_mock.

    Returns:
        A Profiles-shaped group metadata dict.
    """
    payload = {
        "id": group_id,
        "name": name,
        "url": f"https://hcommons-dev.org/groups/{slug or group_id}/",
        "visibility": "public",
        "description": f"Description for {name}",
        "avatar": (
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/"
            "images/mystery-group.png"
        ),
        "groupblog": "",
        "upload_roles": ["member", "moderator", "administrator"],
        "moderate_roles": ["moderator", "administrator"],
    }
    if slug:
        payload["slug"] = slug
    return payload


def _identity_with_roles(user):
    """Identity with base needs plus the user's assigned roles.

    Returns:
        The user's identity with `any_user` and `authenticated_user` needs.
    """
    identity = get_identity(user)
    identity.provides.add(any_user)
    identity.provides.add(authenticated_user)
    return identity


def test_collections_service_associate_success(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
):
    """Associate links an unlinked community and preserves its metadata title."""
    with app.app_context():
        community = minimal_community_factory(slug="orphan-collection")
        original_title = community.to_dict()["metadata"]["title"]
        group_id = "2001001"
        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ]["url"]
        requests_mock.get(
            update_url + group_id,
            json=_api_group(group_id, "Associate Target", slug="associate-target"),
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )

        updated = current_collections.associate(
            system_identity,
            "orphan-collection",
            group_id,
            "knowledgeCommons",
        )
        data = updated.to_dict()
        assert data["metadata"]["title"] == original_title
        assert data["custom_fields"]["kcr:commons_instance"] == "knowledgeCommons"
        assert data["custom_fields"]["kcr:commons_group_id"] == group_id
        assert data["custom_fields"]["kcr:commons_group_name"] == "Associate Target"


def test_collections_service_associate_idempotent(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
):
    """Associating the same group again returns the existing link."""
    with app.app_context():
        minimal_community_factory(slug="idempotent-collection")
        group_id = "2001002"
        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ]["url"]
        requests_mock.get(
            update_url + group_id,
            json=_api_group(group_id, "Idempotent Group"),
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )
        first = current_collections.associate(
            system_identity,
            "idempotent-collection",
            group_id,
            "knowledgeCommons",
        )
        second = current_collections.associate(
            system_identity,
            "idempotent-collection",
            group_id,
            "knowledgeCommons",
        )
        assert first["id"] == second["id"]
        assert second.to_dict()["custom_fields"]["kcr:commons_group_id"] == group_id


def test_collections_service_associate_already_linked_conflict(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
):
    """Associate rejects collections already linked to a different group."""
    with app.app_context():
        linked = _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        with pytest.raises(CollectionAlreadyExistsError):
            current_collections.associate(
                system_identity,
                linked.data["slug"],
                "9999999",
                "knowledgeCommons",
            )


def test_collections_service_associate_uniqueness_conflict(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
):
    """Associate rejects when the target KC group already owns a collection."""
    with app.app_context():
        _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        Community.index.refresh()
        orphan = minimal_community_factory(slug="another-orphan")
        with pytest.raises(CollectionAlreadyExistsError):
            current_collections.associate(
                system_identity,
                orphan.data["slug"],
                _INKLINGS_GROUP_ID,
                "knowledgeCommons",
            )


def test_collections_service_associate_forbidden_owner_without_kc_admin(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
    UserFixture,
):
    """Community owner without write capability or KC admin cannot associate."""
    from invenio_records_resources.services.errors import PermissionDeniedError

    with app.app_context():
        u = UserFixture(
            email="owner-no-kc-admin@example.org",
            password="password",
        )
        u.create(app, db)
        owner = u.user
        community = minimal_community_factory(
            owner=owner.id, slug="owned-no-kc-admin"
        )
        identity = _identity_with_roles(owner)
        with pytest.raises(PermissionDeniedError):
            current_collections.associate(
                identity,
                community.data["slug"],
                "2001003",
                "knowledgeCommons",
            )


def test_collections_service_associate_owner_with_kc_admin(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
    UserFixture,
):
    """Owner plus KC admin role may associate without write capability."""
    with app.app_context():
        u = UserFixture(
            email="owner-with-kc-admin@example.org",
            password="password",
        )
        u.create(app, db)
        owner = u.user
        community = minimal_community_factory(
            owner=owner.id, slug="owned-with-kc-admin"
        )
        group_id = "2001004"
        role_name = f"knowledgeCommons---{group_id}|administrator"
        role = current_accounts.datastore.find_or_create_role(name=role_name)
        current_accounts.datastore.commit()
        # Role/user can land in different SQLAlchemy sessions across fixtures.
        owner = db.session.merge(owner)
        role = db.session.merge(role)
        current_accounts.datastore.add_role_to_user(owner, role)
        current_accounts.datastore.commit()

        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ]["url"]
        requests_mock.get(
            update_url + group_id,
            json=_api_group(group_id, "Owned Associate"),
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )

        updated = current_collections.associate(
            _identity_with_roles(owner),
            community.data["slug"],
            group_id,
            "knowledgeCommons",
        )
        assert updated.to_dict()["custom_fields"]["kcr:commons_group_id"] == group_id


def test_collections_service_transfer_as_system(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
):
    """System identity can transfer a linked collection to another KC group."""
    with app.app_context():
        linked = _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        slug = linked.data["slug"]
        new_group_id = "2002001"
        _mock_profiles_group(
            app,
            requests_mock,
            new_group_id,
            _api_group(new_group_id, "Transfer Target"),
        )

        updated = current_collections.transfer(
            system_identity,
            slug,
            new_group_id,
            "knowledgeCommons",
            old_commons_group_id=_INKLINGS_GROUP_ID,
            old_commons_instance="knowledgeCommons",
        )
        data = updated.to_dict()
        assert data["custom_fields"]["kcr:commons_group_id"] == new_group_id
        assert data["custom_fields"]["kcr:commons_group_name"] == "Transfer Target"


def test_collections_service_transfer_old_mismatch(
    app,
    db,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
):
    """Transfer requires old_* to match the current link."""
    from werkzeug.exceptions import BadRequest

    with app.app_context():
        linked = _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        with pytest.raises(BadRequest):
            current_collections.transfer(
                system_identity,
                linked.data["slug"],
                "2002002",
                "knowledgeCommons",
                old_commons_group_id="0000000",
                old_commons_instance="knowledgeCommons",
            )


def test_collections_service_transfer_forbidden_missing_one_kc_admin(
    app,
    db,
    requests_mock,
    search_clear,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
    UserFixture,
):
    """Owner without write capability needs KC admin on both old and new groups."""
    from invenio_records_resources.services.errors import PermissionDeniedError

    with app.app_context():
        u = UserFixture(
            email="owner-partial-transfer@example.org",
            password="password",
        )
        u.create(app, db)
        owner = u.user
        old_group_id = "2003001"
        new_group_id = "2003002"
        community = minimal_community_factory(
            owner=owner.id,
            slug="transfer-partial-admin",
            custom_fields={
                "kcr:commons_instance": "knowledgeCommons",
                "kcr:commons_group_id": old_group_id,
                "kcr:commons_group_name": "Old Group",
                "kcr:commons_group_description": "",
                "kcr:commons_group_visibility": "public",
            },
        )
        # Admin only for the old group, not the new one.
        old_role_name = f"knowledgeCommons---{old_group_id}|administrator"
        old_role = current_accounts.datastore.find_or_create_role(
            name=old_role_name
        )
        current_accounts.datastore.commit()
        owner = db.session.merge(owner)
        old_role = db.session.merge(old_role)
        current_accounts.datastore.add_role_to_user(owner, old_role)
        current_accounts.datastore.commit()

        with pytest.raises(PermissionDeniedError):
            current_collections.transfer(
                _identity_with_roles(owner),
                community.data["slug"],
                new_group_id,
                "knowledgeCommons",
                old_commons_group_id=old_group_id,
                old_commons_instance="knowledgeCommons",
            )
