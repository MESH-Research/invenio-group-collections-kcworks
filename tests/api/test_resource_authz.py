#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024-2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""HTTP authz and search coverage for the group_collections resource."""

import re
from datetime import timedelta

import arrow
import pytest
from invenio_access.permissions import authenticated_user
from invenio_access.utils import get_identity
from invenio_group_collections_kcworks.scopes import group_collections_write_scope


def test_group_collection_create_role_and_scope_gating(
    running_app,
    db,
    search_clear,
    headers,
    user_factory,
    service_user_factory,
    assign_roles,
    requests_mock,
    mock_send_remote_api_update_fixture,
):
    """POST /group_collections requires write scope and capability (or admin).

    One function exercises six principals against the same create endpoint so
    the heavy app/search setup runs once:

    - admin + write scope → 201 (`Administration`)
    - admin without write scope → 403 (OAuth scope)
    - non-admin, neither role nor write scope → 403
    - non-admin + role, no write scope → 403 (OAuth scope)
    - non-admin + write scope, no role → 403 (permission policy)
    - non-admin + role + write scope → 201
    """
    app = running_app.app
    write_scope = group_collections_write_scope.id
    metadata_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
        "knowledgeCommons"
    ]["url"]

    admin_with_scope = user_factory(
        email="gc-admin-scoped@example.org",
        admin=True,
        token=True,
        oauth_src=None,
        oauth_id=None,
        kc_username=None,
    )
    admin_no_scope = user_factory(
        email="gc-admin-noscope@example.org",
        admin=True,
        token=True,
        scopes=[],
        oauth_src=None,
        oauth_id=None,
        kc_username=None,
    )
    neither_u = service_user_factory(
        email="gc-neither@example.org",
        token=True,
        scopes=[],
    )
    role_only_u, _role_only_id = assign_roles(
        service_user_factory(
            email="gc-role-only@example.org",
            token=True,
            scopes=[],
        ),
        ("group-collections-write",),
    )
    scope_only_u = service_user_factory(
        email="gc-scope-only@example.org",
        token=True,
        scopes=[write_scope],
    )
    both_u, _both_id = assign_roles(
        service_user_factory(
            email="gc-both@example.org",
            token=True,
            scopes=[write_scope],
        ),
        ("group-collections-write",),
    )

    cases = (
        ("admin_with_write_scope", admin_with_scope.allowed_token, 201),
        ("admin_without_write_scope", admin_no_scope.allowed_token, 403),
        ("nonadmin_neither", neither_u.allowed_token, 403),
        ("nonadmin_role_only", role_only_u.allowed_token, 403),
        ("nonadmin_scope_only", scope_only_u.allowed_token, 403),
        ("nonadmin_role_and_scope", both_u.allowed_token, 201),
    )

    with app.test_client() as client:
        for index, (label, token, expected_status) in enumerate(cases):
            group_id = str(91000 + index)
            api_response = {
                "id": group_id,
                "name": f"Gating Group {index}",
                "description": "Permission matrix group",
                "visibility": "public",
                "url": f"https://hcommons.org/groups/gating-group-{index}/",
                "avatar": (
                    "https://hcommons.org/app/plugins/buddypress/bp-core/"
                    "images/mystery-group.png"
                ),
                "upload_roles": ["member"],
                "moderate_roles": ["administrator"],
            }
            requests_mock.get(metadata_url + group_id, json=api_response)
            requests_mock.get(api_response["avatar"], status_code=404)

            response = client.post(
                "/group_collections/",
                json={
                    "commons_instance": "knowledgeCommons",
                    "commons_group_id": group_id,
                },
                headers={**headers, "Authorization": f"Bearer {token}"},
            )
            assert response.status_code == expected_status, (
                f"{label}: expected {expected_status}, got {response.status_code}: "
                f"{response.get_json()}"
            )


def test_group_collection_read_all(
    running_app,
    db,
    search_clear,
    headers,
    user_factory,
    sample_communities_factory,
    communities_links_factory,
    mock_send_remote_api_update_fixture,
):
    """Test the group collections API read all."""
    app = running_app.app
    u = user_factory(token=True)
    token = u.allowed_token
    identity = get_identity(u.user)
    identity.provides.add(authenticated_user)

    sample_communities_factory()

    with app.test_client() as client:
        response = client.get(
            "/group_collections?size=4",
            follow_redirects=True,
            headers={**headers, "Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        # Search defaults commons_instance to knowledgeCommons (4 sample hits).
        assert response.json["hits"]["total"] == 4
        assert len(response.json["hits"]["hits"]) == 4
        assert response.json["sortBy"] == "updated-desc"
        assert response.json["links"] == {
            "self": (
                f"{app.config['SITE_API_URL']}/communities?"
                "page=1&q=%2Bcustom_fields.kcr%5C:commons_instance:knowledgeCommons+"
                "&size=4&sort=updated-desc"
            ),
        }
        for hit in response.json["hits"]["hits"]:
            assert re.match(
                r"^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$",
                hit["id"],
            )
            assert hit["access"] == {
                "member_policy": "open",
                "members_visibility": "public",
                "record_submission_policy": "open",
                "review_policy": "closed",
                "visibility": "public",
            }
            assert hit["children"] == {"allow": False}
            assert arrow.utcnow() - arrow.get(hit["created"]) < timedelta(seconds=3)
            assert hit["links"] == communities_links_factory(hit["id"], hit["slug"])
            assert hit["metadata"]["curation_policy"] == "Curation policy"
            assert "description" in hit["metadata"]["description"]
            assert "Organization" in hit["metadata"]["organizations"][0]["name"]
            assert "Information for" in hit["metadata"]["page"]
            assert re.match(r"^(?:MSU )?Community \d+$", hit["metadata"]["title"])
            assert hit["metadata"]["website"]
            assert hit["metadata"]["type"]["id"] in [
                "event",
                "commons",
                "group",
                "organization",
            ]
            assert arrow.utcnow() - arrow.get(hit["updated"]) < timedelta(seconds=3)
            assert re.match(r"^(?:msu-)?community-\d+$", hit["slug"])
            assert hit["custom_fields"]["kcr:commons_group_description"]
            assert hit["custom_fields"]["kcr:commons_group_name"]
            assert hit["custom_fields"]["kcr:commons_group_id"]
            assert hit["custom_fields"]["kcr:commons_group_visibility"]
            assert hit["custom_fields"]["kcr:commons_instance"] == "knowledgeCommons"


@pytest.mark.skip(reason="Not implemented")
def test_group_collections_read_one(
    running_app, db, search_clear, headers, user_factory
):
    """Test the group collections API read one."""
    pass
