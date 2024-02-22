import pytest


@pytest.mark.parametrize(
    "url,expected_response_code,expected_json",
    [
        ("/api/group_collections", 404, "Hello, World!"),
        ("/api/group_collections/collection-1", 404, "Hello, World!"),
        (
            "/api/group_collections/",
            200,
            {
                "aggregations": {
                    "type": {
                        "buckets": [
                            {
                                "doc_count": 1,
                                "is_selected": False,
                                "key": "event",
                                "label": "Event",
                            },
                            {
                                "doc_count": 1,
                                "is_selected": False,
                                "key": "organization",
                                "label": "Organization",
                            },
                        ],
                        "label": "Type",
                    },
                    "visibility": {
                        "buckets": [
                            {
                                "doc_count": 2,
                                "is_selected": False,
                                "key": "public",
                                "label": "Public",
                            }
                        ],
                        "label": "Visibility",
                    },
                },
                "hits": {
                    "hits": [
                        {
                            "access": {
                                "member_policy": "open",
                                "record_policy": "open",
                                "review_policy": "closed",
                                "visibility": "public",
                            },
                            "children": {"allow": False},
                            "created": "2024-02-22T00:32:33.660458+00:00",
                            "custom_fields": {
                                "kcr:commons_group_id": "456",
                                "kcr:commons_group_name": "Commons Group 2",
                                "kcr:commons_group_description": (
                                    "Commons Group 2 description"
                                ),
                                "kcr:commons_group_visibility": "public",
                            },
                            "deletion_status": {
                                "is_deleted": False,
                                "status": "P",
                            },
                            "id": "b3f00322-c724-40e2-88e3-da0a62756c5d",
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
                            "metadata": {
                                "curation_policy": "Curation policy",
                                "description": "Community 2 description",
                                "organizations": [{"name": "Organization 2"}],
                                "page": "Information for community 2",
                                "title": "Community 2",
                                "type": {
                                    "id": "organization",
                                    "title": {"en": "Organization"},
                                },
                                "website": "https://community2.com",
                            },
                            "revision_id": 2,
                            "slug": "community-2",
                            "updated": "2024-02-22T00:32:33.677774+00:00",
                        },
                        {
                            "access": {
                                "member_policy": "open",
                                "record_policy": "open",
                                "review_policy": "closed",
                                "visibility": "public",
                            },
                            "children": {"allow": False},
                            "created": "2024-02-22T00:32:33.621409+00:00",
                            "custom_fields": {
                                "kcr:commons_group_id": "123",
                                "kcr:commons_group_name": "Commons Group 1",
                                "kcr:commons_group_description": "Commons "
                                "Group 1 description",
                                "kcr:commons_group_visibility": "public",
                            },
                            "deletion_status": {
                                "is_deleted": False,
                                "status": "P",
                            },
                            "id": "b0409cce-dc7e-4299-895f-fd0fab1c2f9b",
                            "links": {
                                "featured": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/"
                                "featured",
                                "invitations": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/"
                                "invitations",
                                "logo": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/logo",
                                "members": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/members",
                                "public_members": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/"
                                "members/public",
                                "records": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/records",
                                "rename": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/rename",
                                "requests": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b/"
                                "requests",
                                "self": "https://127.0.0.1:5000/api/"
                                "communities/"
                                "b0409cce-dc7e-4299-895f-fd0fab1c2f9b",
                                "self_html": "https://127.0.0.1:5000/"
                                "communities/community-1",
                                "settings_html": "https://127.0.0.1:5000/"
                                "communities/community-1/settings",
                            },
                            "metadata": {
                                "curation_policy": "Curation policy",
                                "description": "Community 1 description",
                                "organizations": [{"name": "Organization 1"}],
                                "page": "Information for community 1",
                                "title": "Community 1",
                                "type": {
                                    "id": "event",
                                    "title": {"en": "Event"},
                                },
                                "website": "https://community1.com",
                            },
                            "revision_id": 2,
                            "slug": "community-1",
                            "updated": "2024-02-22T00:32:33.648444+00:00",
                        },
                    ],
                    "total": 2,
                },
                "links": {
                    "self": "https://127.0.0.1:5000/api/communities"
                    "?page=1&q=&size=25&sort=newest"
                },
                "sortBy": "newest",
            },
        ),
    ],
)
def test_group_collections_resource_get(
    testapp,
    client,
    sample_communities,
    community_type_v,
    db,
    location,
    url,
    expected_json,
    expected_response_code,
):
    actual = client.get(url)
    assert actual.status_code == expected_response_code
    if expected_response_code == 200:
        assert actual.json["aggregations"] == expected_json["aggregations"]
        assert actual.json["sortBy"] == expected_json["sortBy"]
        assert actual.json["links"] == expected_json["links"]
        for idx, h in enumerate(actual.json["hits"]["hits"]):
            assert h["access"] == expected_json["hits"]["hits"][idx]["access"]
            assert "created" in h.keys()
            # h['created'] == expected_json['hits']['hits'][0]['created']
            assert (
                h["deletion_status"]
                == expected_json["hits"]["hits"][idx]["deletion_status"]
            )
            assert "id" in h.keys()
            # assert h["id"] == expected_json["hits"]["hits"][0]["id"]
            assert "links" in h.keys()
            # h['links'] == expected_json['hits']['hits'][0]['links']
            assert (
                h["metadata"] == expected_json["hits"]["hits"][idx]["metadata"]
            )
            assert (
                h["revision_id"]
                == expected_json["hits"]["hits"][idx]["revision_id"]
            )
            assert h["slug"] == expected_json["hits"]["hits"][idx]["slug"]
            assert "updated" in h.keys()
            # h['updated'] = expected_json['hits']['hits'][0]['updated']
    else:
        assert actual.json == expected_json
