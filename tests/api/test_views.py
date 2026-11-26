#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024-2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""HTTP resource tests for the group_collections API."""

import json
from copy import deepcopy
from urllib.parse import parse_qs, unquote_plus, urlparse

import pytest

# Module-local Profiles stubs for create/delete/not-found view tests.
_AVATAR_URL = (
    "https://hcommons-dev.org/app/plugins/buddypress/bp-core/"
    "images/mystery-group.png"
)
_INKLINGS_GROUP_ID = "1004290"
_INKLINGS_REMOTE = {
    "id": _INKLINGS_GROUP_ID,
    "name": "The Inklings",
    "url": "https://hcommons-dev.org/groups/the-inklings/",
    "visibility": "public",
    "description": (
        "For scholars interested in J.R.R. Tolkien, C. S. Lewis, "
        "Charles Williams, and other writers associated with the Inklings."
    ),
    "avatar": _AVATAR_URL,
    "groupblog": "",
    "upload_roles": ["member", "moderator", "administrator"],
    "moderate_roles": ["moderator", "administrator"],
}
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


def _mock_profiles_group(app, requests_mock, group_id: str, payload: dict) -> None:
    """Stub Profiles group GET + avatar fetch."""
    update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
        "knowledgeCommons"
    ]["url"]
    requests_mock.get(update_url + group_id, status_code=200, json=payload)
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


communities_data = {
    "knowledgeCommons": [
        (
            "123",
            "Commons Group 1",
            "Community 1",
        ),
        (
            "456",
            "Commons Group 2",
            "Community 2",
        ),
        (
            "789",
            "Commons Group 3",
            "Community 3",
        ),
        (
            "101112",
            "Commons Group 4",
            "Community 4",
        ),
    ],
    "msuCommons": [
        (
            "131415",
            "MSU Group 1",
            "MSU Community 1",
        ),
        (
            "161718",
            "MSU Group 2",
            "MSU Community 2",
        ),
        (
            "192021",
            "MSU Group 3",
            "MSU Community 3",
        ),
        (
            "222324",
            "MSU Group 4",
            "MSU Community 4",
        ),
    ],
}

sample_communities_hits = []
for instance in communities_data:
    for c in communities_data[instance]:
        slug = c[2].lower().replace("-", "").replace(" ", "")
        data = {
            "id": "b3f00322-c724-40e2-88e3-da0a62756c5d",
            "created": "2024-02-22T00:32:33.660458+00:00",
            "access": {
                "visibility": "public",
                "member_policy": "open",
                "record_submission_policy": "open",
                "review_policy": "closed",
                "members_visibility": "public",
            },
            "children": {"allow": False},
            "slug": c[2].lower().replace(" ", "-"),
            "metadata": {
                "title": c[2],
                "description": c[2] + " description",
                "type": {"id": "event", "title": {"en": "Event"}},
                "curation_policy": "Curation policy",
                "page": f"Information for {c[2].lower()}",
                "website": f"https://{slug}.com",
                "organizations": [
                    {
                        "name": "Organization 1",
                    }
                ],
            },
            "custom_fields": {
                "kcr:commons_instance": instance,
                "kcr:commons_group_id": c[0],
                "kcr:commons_group_name": c[1],
                "kcr:commons_group_description": (f"{c[1]} description"),
                "kcr:commons_group_visibility": "public",
            },
            "deletion_status": {
                "is_deleted": False,
                "status": "P",
            },
            "links": {
                "featured": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/"
                "featured",
                "invitations": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/"
                "invitations",
                "logo": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/logo",
                "members": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/members",
                "public_members": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/members/"
                "public",
                "records": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/records",
                "rename": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/rename",
                "requests": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d/"
                "requests",
                "self": "https://127.0.0.1:5000/api/"
                "communities/"
                "b3f00322-c724-40e2-88e3-da0a62756c5d",
                "self_html": "https://127.0.0.1:5000/communities/community-2",
                "settings_html": "https://127.0.0.1:5000/"
                "communities/community-2/settings",
            },
            "revision_id": 2,
            "updated": "2024-02-22T00:32:33.677774+00:00",
        }
        sample_communities_hits.append(data)

sample_communities_hits.reverse()
sample_communities_data = {
    "aggregations": {
        "type": {
            "buckets": [
                {
                    "doc_count": 8,
                    "is_selected": False,
                    "key": "event",
                    "label": "Event",
                },
            ],
            "label": "Type",
        },
        "visibility": {
            "buckets": [
                {
                    "doc_count": 8,
                    "is_selected": False,
                    "key": "public",
                    "label": "Public",
                }
            ],
            "label": "Visibility",
        },
    },
    "hits": {
        "hits": sample_communities_hits,
        "total": 8,
    },
    "links": {
        "self": "https://127.0.0.1:5000/api/communities?page=1&q=&size=25&sort=newest",
    },
    "sortBy": "newest",
}


@pytest.mark.parametrize(
    "idx,url,expected_response_code,expected_json_base",
    [
        (
            0,
            "/group_collections?sort=newest",
            200,
            sample_communities_data,
        ),
        (
            1,
            "/group_collections?commons_instance=knowledgeCommons&sort=newest",
            200,
            sample_communities_data,
        ),
        (
            2,
            "/group_collections?commons_instance=knowledgeCommons"
            "&commons_group_id=456&sort=newest",
            200,
            sample_communities_data,
        ),
        (
            3,
            "/group_collections?sort=newest&size=4&page=2",
            200,
            sample_communities_data,
        ),
        (
            4,
            "/group_collections?commons_instance=nonexistentCommons&sort=newest",
            404,
            {
                "message": "No Works collection found matching the parameters"
                r" +custom_fields.kcr\:commons_instance:nonexistentCommons ",
                "status": 404,
            },
        ),
        (
            5,
            "/group_collections?commons_instance=msuCommons"
            "&commons_group_id=77777&sort=newest",
            404,
            {
                "message": "No Works collection found matching the parameters"
                r" +custom_fields.kcr\:commons_instance:msuCommons "
                r"+custom_fields.kcr\:commons_group_id:77777",
                "status": 404,
            },
        ),
        (
            6,
            "/group_collections?size=1&sort=newest",
            400,
            {
                "message": "{'size': ['Must be greater than or equal to "
                "4 and less than or equal to 1000.']}",
                "status": 400,
            },
        ),
        (
            7,
            "/group_collections?commons_instance=knowledgeCommons"
            "&group_id=1003911&sort=newest",
            400,
            {
                "message": "{'group_id': ['Unknown field.']}",
                "status": 400,
            },
        ),
    ],
)
def test_group_collections_resource_search(
    app,
    client,
    sample_communities_factory,
    community_type_v,
    location,
    admin,
    search_clear,
    idx,
    url,
    expected_json_base,
    expected_response_code,
):
    """Search group collections with filters, paging, and validation errors."""
    sample_communities_factory()
    expected_json = deepcopy(expected_json_base)
    headers = {
        "Authorization": f"Bearer {admin.allowed_token}",
        "accept": "application/json",
    }

    actual = client.get(url, follow_redirects=True, headers=headers)

    assert actual.status_code == expected_response_code, (
        f"url={url!r} status={actual.status_code} body={actual.get_json()}"
    )

    if expected_response_code == 200:
        if idx == 2:
            expected_json["hits"]["total"] = 1
            expected_json["hits"]["hits"] = [
                h
                for h in expected_json["hits"]["hits"]
                if h["custom_fields"]["kcr:commons_group_id"] == "456"
            ]
            for a in expected_json["aggregations"]:
                for b in expected_json["aggregations"][a]["buckets"]:
                    b["doc_count"] = 1
        if idx in (0, 1):
            # Unfiltered search defaults commons_instance to knowledgeCommons.
            expected_json["hits"]["total"] = 4
            expected_json["hits"]["hits"] = [
                h
                for h in expected_json["hits"]["hits"]
                if h["custom_fields"]["kcr:commons_instance"] == "knowledgeCommons"
            ]
            for a in expected_json["aggregations"]:
                for b in expected_json["aggregations"][a]["buckets"]:
                    b["doc_count"] = 4
        if idx == 3:
            # Page 2 of the default knowledgeCommons set (4 hits, size 4) is
            # empty; communities search still reports total=4.
            expected_json["hits"]["total"] = 4
            expected_json["hits"]["hits"] = []
            for a in expected_json["aggregations"]:
                for b in expected_json["aggregations"][a]["buckets"]:
                    b["doc_count"] = 4

        assert actual.json["aggregations"] == expected_json["aggregations"]
        assert actual.json["sortBy"] == expected_json["sortBy"]
        # Link encoding differs (+ vs %20 / %2B); compare decoded query intent.
        actual_self = actual.json["links"]["self"]
        parsed = urlparse(actual_self)
        assert parsed.path.rstrip("/").endswith("communities")
        qs = parse_qs(parsed.query)
        assert qs.get("sort") == ["newest"]
        q = unquote_plus(qs.get("q", [""])[0])
        assert "custom_fields.kcr\\:commons_instance:knowledgeCommons" in q
        if idx == 2:
            assert "custom_fields.kcr\\:commons_group_id:456" in q
        if idx == 3:
            assert qs.get("size") == ["4"]
            assert qs.get("page") == ["2"]
            assert actual.json["hits"]["hits"] == []
            assert actual.json["hits"]["total"] == 4
        else:
            for i, h in enumerate(actual.json["hits"]["hits"]):
                assert h["access"] == expected_json["hits"]["hits"][i]["access"]
                assert "created" in h.keys()
                assert (
                    h["deletion_status"]
                    == expected_json["hits"]["hits"][i]["deletion_status"]
                )
                assert "id" in h.keys()
                assert "links" in h.keys()
                assert h["metadata"] == expected_json["hits"]["hits"][i]["metadata"]
                assert (
                    h["revision_id"]
                    == expected_json["hits"]["hits"][i]["revision_id"]
                )
                assert h["slug"] == expected_json["hits"]["hits"][i]["slug"]
                assert "updated" in h.keys()
    else:
        assert actual.json == expected_json


@pytest.mark.parametrize(
    "url,expected_response_code,expected_json",
    [
        (
            "/group_collections/collection-nonexistent",
            404,
            {
                "message": "No collection found with the slug collection-nonexistent",
                "status": 404,
            },
        ),
        (
            "/group_collections/community-1",
            200,
            [
                c
                for c in sample_communities_data["hits"]["hits"]
                if c["slug"] == "community-1"
            ][0],
        ),
    ],
)
def test_group_collections_resource_read(
    app,
    client,
    sample_communities_factory,
    community_type_v,
    location,
    admin,
    search_clear,
    url,
    expected_json,
    expected_response_code,
):
    """Read a group collection by slug (found and not found)."""
    sample_communities_factory()
    headers = {
        "Authorization": f"Bearer {admin.allowed_token}",
        "accept": "application/json",
    }
    actual_resp = client.get(url, follow_redirects=True, headers=headers)
    assert actual_resp.status_code == expected_response_code
    actual = actual_resp.json
    if expected_response_code == 200:
        assert actual["access"] == expected_json["access"]
        assert "created" in actual.keys()
        # h['created'] == expected_json['hits']['hits'][0]['created']
        assert actual["deletion_status"] == expected_json["deletion_status"]
        assert "id" in actual.keys()
        # assert actual["id"] == expected_json["hits"]["hits"][0]["id"]
        assert "links" in actual.keys()
        # actual['links'] == expected_json['hits']['hits'][0]['links']
        assert actual["metadata"] == expected_json["metadata"]
        assert actual["revision_id"] == expected_json["revision_id"]
        assert actual["slug"] == expected_json["slug"]
        assert "updated" in actual.keys()
        # h['updated'] = expected_json['hits']['hits'][0]['updated']
    else:
        assert actual == expected_json


@pytest.mark.parametrize(
    "request_payload,expected_json,expected_response_code",
    [
        (
            {
                "commons_instance": "knowledgeCommons",
                "commons_group_id": "1004290",
                "collection_visibility": "public",
            },
            {
                "commons_group_id": "1004290",
                "collection": "the-inklings",
            },
            201,
        )
    ],
)
def test_group_collections_resource_create(
    app,
    client,
    db,
    admin,
    location,
    request_payload,
    expected_json,
    expected_response_code,
    search_clear,
    requests_mock,
    create_communities_custom_fields,
):
    """POST creates a linked group collection from Commons group metadata."""
    with app.test_client() as client:
        _mock_profiles_group(
            app, requests_mock, _INKLINGS_GROUP_ID, _INKLINGS_REMOTE
        )

        headers = {
            "Authorization": f"Bearer {admin.allowed_token}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        actual_resp = client.post(
            "/group_collections",
            data=json.dumps(request_payload),
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == expected_response_code
        actual = actual_resp.json
        if expected_response_code == 201:
            assert actual["commons_group_id"] == expected_json["commons_group_id"]
            assert actual["collection"] == expected_json["collection"]
        else:
            assert actual == expected_json


def test_collections_resource_create_unauthorized(
    app,
    client,
    db,
    location,
    search_clear,
):
    """POST with an invalid bearer token is rejected."""
    with app.test_client() as client:
        headers = {
            "Authorization": "Bearer invalid-token",
            "content-type": "application/json",
            "accept": "application/json",
        }

        actual_resp = client.post(
            "/group_collections",
            data=json.dumps({
                "commons_instance": "knowledgeCommons",
                "commons_group_id": _INKLINGS_GROUP_ID,
                "collection_visibility": "public",
            }),
            follow_redirects=True,
            headers=headers,
        )
        # Invalid bearer is rejected by oauth before CSRF checks.
        assert actual_resp.status_code == 400
        assert actual_resp.json["status"] == 400
        assert "message" in actual_resp.json


def test_collections_resource_not_found(
    app,
    client,
    admin,
    db,
    location,
    search_clear,
    requests_mock,
):
    """POST returns 404 when the Commons group does not exist."""
    with app.test_client() as client:
        missing_id = "100429011"
        _mock_profiles_group(app, requests_mock, missing_id, _NOT_FOUND_REMOTE)

        headers = {
            "Authorization": f"Bearer {admin.allowed_token}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        actual_resp = client.post(
            "/group_collections",
            data=json.dumps({
                "commons_instance": "knowledgeCommons",
                "commons_group_id": missing_id,
                "collection_visibility": "public",
            }),
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 404
        assert actual_resp.json == {
            "message": (
                f"No such group {missing_id} could be found on Knowledge Commons"
            ),
            "status": 404,
        }


def test_collections_resource_delete(
    app,
    client,
    db,
    location,
    admin,
    search_clear,
    requests_mock,
    create_communities_custom_fields,
    minimal_community_factory,
):
    """DELETE removes a linked collection; subsequent read returns 410."""
    with app.test_client() as client:
        created_collection = _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        assert created_collection.data["slug"] == "the-inklings"

        headers = {
            "Authorization": f"Bearer {admin.allowed_token}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        actual_resp = client.delete(
            "/group_collections/the-inklings",
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 400
        assert actual_resp.json["status"] == 400
        assert "commons_group_id" in actual_resp.json["message"]

        # commons_instance defaults to knowledgeCommons when omitted.
        actual_resp = client.delete(
            "/group_collections/the-inklings",
            query_string={"commons_group_id": _INKLINGS_GROUP_ID},
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 204

        actual_resp = client.get(
            "/group_collections/the-inklings",
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 410
        assert actual_resp.json == {
            "message": "The collection has been deleted.",
            "status": 410,
        }


def test_group_collections_resource_associate(
    app,
    client,
    db,
    admin,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
    search_clear,
    requests_mock,
):
    """PATCH /group_collections/<slug>/associate links an existing collection."""
    with app.test_client() as client:
        community = minimal_community_factory(slug="view-associate-me")
        group_id = "3001001"
        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ]["url"]
        requests_mock.get(
            update_url + group_id,
            status_code=200,
            json={
                "id": group_id,
                "name": "View Associate Group",
                "url": "https://hcommons-dev.org/groups/view-associate/",
                "visibility": "public",
                "description": "Associated via view test",
                "avatar": (
                    "https://hcommons-dev.org/app/plugins/buddypress/bp-core/"
                    "images/mystery-group.png"
                ),
                "upload_roles": ["member", "moderator", "administrator"],
                "moderate_roles": ["moderator", "administrator"],
            },
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )

        headers = {
            "Authorization": f"Bearer {admin.allowed_token}",
            "content-type": "application/json",
            "accept": "application/json",
        }
        resp = client.patch(
            f"/group_collections/{community.data['slug']}/associate",
            data=json.dumps({
                "commons_instance": "knowledgeCommons",
                "commons_group_id": group_id,
            }),
            follow_redirects=True,
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json
        assert body["commons_group_id"] == group_id
        assert body["collection"] == "view-associate-me"
        assert body["collection_id"] == community.data["id"]


def test_group_collections_resource_transfer(
    app,
    client,
    db,
    admin,
    location,
    create_communities_custom_fields,
    minimal_community_factory,
    search_clear,
    requests_mock,
):
    """PATCH /group_collections/<slug>/transfer moves KC group ownership."""
    with app.test_client() as client:
        linked = _linked_collection(
            minimal_community_factory,
            group_id=_INKLINGS_GROUP_ID,
            slug="the-inklings",
        )
        new_group_id = "3002001"
        _mock_profiles_group(
            app,
            requests_mock,
            new_group_id,
            {
                "id": new_group_id,
                "name": "View Transfer Group",
                "url": "https://hcommons-dev.org/groups/view-transfer/",
                "visibility": "public",
                "description": "Transferred via view test",
                "avatar": _AVATAR_URL,
                "upload_roles": ["member", "moderator", "administrator"],
                "moderate_roles": ["moderator", "administrator"],
            },
        )

        headers = {
            "Authorization": f"Bearer {admin.allowed_token}",
            "content-type": "application/json",
            "accept": "application/json",
        }
        resp = client.patch(
            f"/group_collections/{linked.data['slug']}/transfer",
            data=json.dumps({
                "commons_instance": "knowledgeCommons",
                "commons_group_id": new_group_id,
                "old_commons_instance": "knowledgeCommons",
                "old_commons_group_id": _INKLINGS_GROUP_ID,
            }),
            follow_redirects=True,
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json
        assert body["commons_group_id"] == new_group_id
        assert body["old_commons_group_id"] == _INKLINGS_GROUP_ID
        assert body["collection"] == linked.data["slug"]


def test_group_collections_resource_legacy_patch_not_implemented(
    app,
    client,
    admin,
    db,
):
    """PATCH /group_collections/<slug> points callers to associate/transfer."""
    with app.test_client() as client:
        headers = {
            "Authorization": f"Bearer {admin.allowed_token}",
            "content-type": "application/json",
            "accept": "application/json",
        }
        resp = client.patch(
            "/group_collections/some-slug",
            data=json.dumps({}),
            follow_redirects=True,
            headers=headers,
        )
        assert resp.status_code == 501
        assert "/associate" in resp.json["message"]
        assert "/transfer" in resp.json["message"]
