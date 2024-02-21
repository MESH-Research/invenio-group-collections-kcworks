import pytest


def test_group_collections_resource_get(testapp, client):
    print(testapp.extensions["invenio-groups"].service)
    print(testapp.extensions["invenio-groups"].resource)
    print(testapp.blueprints)
    res = client.get("https://localhost:5000/api/group_collections")
    res = client.get("https://localhost/api/records")
    assert res.status_code == 200
    assert res.json == {"message": "Hello, World!"}
