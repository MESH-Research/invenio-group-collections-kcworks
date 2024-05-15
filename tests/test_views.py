from copy import deepcopy
import json
import pytest

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
                "record_policy": "open",
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
                "self_html": "https://127.0.0.1:5000/"
                "communities/community-2",
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
        "self": "https://127.0.0.1:5000/api/communities"
        "?page=1&q=&size=25&sort=newest",
    },
    "sortBy": "newest",
}


@pytest.mark.parametrize(
    "idx,url,expected_response_code,expected_json_base",
    [
        (
            0,
            "/group_collections/?sort=newest",
            200,
            sample_communities_data,
        ),
        (
            1,
            "/group_collections?commons_instance=knowledgeCommons"
            "&sort=newest",
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
            "/group_collections?commons_instance=nonexistentCommons"
            "&sort=newest",
            404,
            {
                "message": "No Works collection found matching the parameters"
                " +_exists_:custom_fields.kcr\:commons_instance +custom_fields.kcr\:commons_instance:nonexistentCommons ",
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
                " +_exists_:custom_fields.kcr\:commons_instance +custom_fields.kcr\:commons_instance:msuCommons "
                "+custom_fields.kcr\:commons_group_id:77777",
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
    ],
)
def test_group_collections_resource_search(
    app,
    client,
    sample_communities,
    community_type_v,
    location,
    communities_service,
    idx,
    url,
    expected_json_base,
    expected_response_code,
):
    sample_communities(app, communities_service)
    expected_json = deepcopy(expected_json_base)

    actual = client.get(url, follow_redirects=True)

    assert actual.status_code == expected_response_code

    if expected_response_code == 200:
        if idx == 3:
            expected_json["links"][
                "next"
            ] = "https://127.0.0.1:5000/api/communities?page=2&q=&size=4&sort=newest"
            expected_json["links"] = {
                "prev": "https://127.0.0.1:5000/api/communities?page=1&q=%2B_exists_%3Acustom_fields.kcr%5C%3Acommons_instance%20&size=4&sort=newest",
                "self": "https://127.0.0.1:5000/api/communities?page=2&q=%2B_exists_%3Acustom_fields.kcr%5C%3Acommons_instance%20&size=4&sort=newest",
            }
            for a in expected_json["aggregations"]:
                for b in expected_json["aggregations"][a]["buckets"]:
                    b["doc_count"] = 8
            expected_json["hits"]["hits"] = expected_json["hits"]["hits"][4:]
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
            expected_json["links"] = {
                "self": "https://127.0.0.1:5000/api/communities?page=1&q=%2B_exists_%3Acustom_fields.kcr%5C%3Acommons_instance%20%2Bcustom_fields.kcr%5C%3Acommons_instance%3AknowledgeCommons%20%2Bcustom_fields.kcr%5C%3Acommons_group_id%3A456&size=25&sort=newest"
            }
        if idx == 1:
            expected_json["hits"]["total"] = 4
            expected_json["hits"]["hits"] = [
                h
                for h in expected_json["hits"]["hits"]
                if h["custom_fields"]["kcr:commons_instance"]
                == "knowledgeCommons"
            ]
            for a in expected_json["aggregations"]:
                for b in expected_json["aggregations"][a]["buckets"]:
                    b["doc_count"] = 4
            expected_json["links"] = {
                "self": "https://127.0.0.1:5000/api/communities?page=1&q=%2B_exists_%3Acustom_fields.kcr%5C%3Acommons_instance%20%2Bcustom_fields.kcr%5C%3Acommons_instance%3AknowledgeCommons%20&size=25&sort=newest"
            }
        if idx == 0:
            expected_json["links"] = {
                "self": "https://127.0.0.1:5000/api/communities?page=1&q=%2B_exists_%3Acustom_fields.kcr%5C%3Acommons_instance%20&size=25&sort=newest"
            }

        print("actual hits", [h["slug"] for h in actual.json["hits"]["hits"]])
        print(
            "expected hits", [h["slug"] for h in expected_json["hits"]["hits"]]
        )
        assert actual.json["aggregations"] == expected_json["aggregations"]
        assert actual.json["sortBy"] == expected_json["sortBy"]
        assert actual.json["links"] == expected_json["links"]
        for i, h in enumerate(actual.json["hits"]["hits"]):
            assert h["access"] == expected_json["hits"]["hits"][i]["access"]
            assert "created" in h.keys()
            # h['created'] == expected_json['hits']['hits'][0]['created']
            assert (
                h["deletion_status"]
                == expected_json["hits"]["hits"][i]["deletion_status"]
            )
            assert "id" in h.keys()
            # assert h["id"] == expected_json["hits"]["hits"][0]["id"]
            assert "links" in h.keys()
            # h['links'] == expected_json['hits']['hits'][0]['links']
            assert (
                h["metadata"] == expected_json["hits"]["hits"][i]["metadata"]
            )
            assert (
                h["revision_id"]
                == expected_json["hits"]["hits"][i]["revision_id"]
            )
            assert h["slug"] == expected_json["hits"]["hits"][i]["slug"]
            assert "updated" in h.keys()
            # h['updated'] = expected_json['hits']['hits'][0]['updated']
    else:
        assert actual.json == expected_json


@pytest.mark.parametrize(
    "url,expected_response_code,expected_json",
    [
        (
            "/group_collections/collection-nonexistent",
            404,
            {
                "message": "No collection found with the slug "
                "collection-nonexistent",
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
    sample_communities,
    community_type_v,
    location,
    communities_service,
    url,
    expected_json,
    expected_response_code,
):
    sample_communities(app, communities_service)
    actual_resp = client.get(url, follow_redirects=True)
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
    appctx,
    broker_uri,
    # celery_session_app,
    client,
    db,
    admin,
    location,
    request_payload,
    expected_json,
    expected_response_code,
    sample_community1,
    search_clear,
    requests_mock,
):
    with app.test_client() as client:
        token_actual = admin.allowed_token

        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noqa
        requests_mock.get(
            update_url.replace("{id}", "1004290"),
            status_code=200,
            json=sample_community1["api_response"],
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )

        headers = {
            "Authorization": f"Bearer {token_actual}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        actual_resp = client.post(
            "/group_collections",
            data=json.dumps(request_payload),
            follow_redirects=True,
            headers=headers,
        )
        print(actual_resp.json)
        assert actual_resp.status_code == expected_response_code
        actual = actual_resp.json
        if expected_response_code == 201:
            assert (
                actual["commons_group_id"] == expected_json["commons_group_id"]
            )
            assert actual["collection"] == expected_json["collection"]
        else:
            assert actual == expected_json


def test_collections_resource_create_unauthorized(
    app,
    appctx,
    broker_uri,
    # celery_session_app,
    client,
    db,
    location,
    sample_community1,
    search_clear,
    requests_mock,
):
    with app.test_client() as client:
        token_actual = "invalid-token"

        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noqa

        headers = {
            "Authorization": f"Bearer {token_actual}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        actual_resp = client.post(
            "/group_collections",
            data=json.dumps(
                {
                    "commons_instance": "knowledgeCommons",
                    "commons_group_id": "1004290",
                    "collection_visibility": "public",
                }
            ),
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 400
        assert actual_resp.json == {
            "message": "CSRF cookie not set.",
            "status": 400,
        }


def test_collections_resource_not_found(
    app,
    appctx,
    broker_uri,
    # celery_session_app,
    client,
    admin,
    db,
    location,
    not_found_response_body,
    search_clear,
    requests_mock,
):
    with app.test_client() as client:
        token_actual = admin.allowed_token

        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noqa

        requests_mock.get(
            update_url.replace("{id}", "100429011"),
            status_code=200,
            json=not_found_response_body,
        )

        headers = {
            "Authorization": f"Bearer {token_actual}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        actual_resp = client.post(
            "/group_collections",
            data=json.dumps(
                {
                    "commons_instance": "knowledgeCommons",
                    "commons_group_id": "100429011",
                    "collection_visibility": "public",
                }
            ),
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 404
        assert actual_resp.json == {
            "message": "No such group 100429011 could be found on Knowledge Commons",
            "status": 404,
        }


def test_collections_resource_delete(
    app,
    appctx,
    broker_uri,
    client,
    db,
    location,
    admin,
    sample_community1,
    search_clear,
    requests_mock,
    custom_fields,
):
    with app.test_client() as client:
        token_actual = admin.allowed_token

        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noqa
        requests_mock.get(
            update_url.replace("{id}", "1004290"),
            status_code=200,
            json=sample_community1["api_response"],
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )

        headers = {
            "Authorization": f"Bearer {token_actual}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        created_collection = sample_community1["create_func"]()
        assert created_collection.data["slug"] == "the-inklings"

        actual_resp = client.delete(
            "/group_collections/the-inklings",
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 400
        assert actual_resp.json == {
            "message": "No commons_instance provided",
            "status": 400,
        }

        actual_resp = client.delete(
            "/group_collections/the-inklings",
            query_string={"commons_instance": "knowledgeCommons"},
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 400
        assert actual_resp.json == {
            "message": "No commons_group_id provided",
            "status": 400,
        }

        actual_resp = client.delete(
            "/group_collections/the-inklings",
            query_string={
                "commons_instance": "knowledgeCommons",
                "commons_group_id": "1004290",
            },
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 204

        actual_resp = client.get(
            "/group_collections/the-inklings",
            follow_redirects=True,
            headers=headers,
        )
        assert actual_resp.status_code == 404
        assert actual_resp.json == {
            "message": "No collection found with the slug the-inklings",
            "status": 404,
        }
