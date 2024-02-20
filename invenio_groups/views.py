# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023-2024, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Views for Commons group collections API endpoints.

Two endpoints are exposed by this file:

- https://example.org/api/group_collections
- https://example.org/api/webhooks/group_updates

The `group_collections` API endpoint allows a Commons instance
to create, modify, or delete a collection (community) in Invenio owned
by a Commons group.

The `group_updates` webhook receives signals notifying Invenio that
changes have been made to the metadata of a Commons group. This endpoint is
not used to receive updated group metadata. It only receives notifications
that operations should be performed on a group's collection.

The `group_collections` API endpoint
---------------

## GET

A GET request to this endpoint will retrieve metadata on Invenio collections
that are owned by a Commons group. A request to the bare endpoint without a
group ID or collection slug will return a list of all collections owned by
all Commons groups.

### Query parameters

Four optional query parameters can be used to filter the results:

| Parameter name | Description |
| ---------------|------------ |
| `commons_instance` | the name of the Commons instance to which the group belongs. If this parameter is provided, the response will only include collections owned by groups in that instance. |
| `commons_group_id` | the ID of the Commons group. If this parameter is provided, the response will only include collections owned by that group. |
| `collection` | the slug of the collection. If this parameter is provided, the response will include only metadata for that collection. |
| `page` | the page number of the results |
| `size` | the number of results to include on each page |
| `sort` | the field to sort the results by |
| `order` | the order to sort the results in |

#### Sorting

The results can be sorted by the following fields:

| Field name | Description |
| -----------|-------------|
| `title` | the title of the collection |
| `created` | the date the collection was created |
| `updated` | the date the collection was last updated |
| `commons_group_id` | the ID of the Commons group that owns the collection |
| `commons_group_title` | the title of the Commons group that owns the collection |
| `size` | the number of records in the collection |

By default the results are sorted by `updated`

Sort order is descending by default, unless "ascending" is provided as a value for the `order` query parameter.

#### Pagination

If there are more than 10 results they will be paginated. The response will include links to the first, last, previous, and next pages of results--both in the `Link` response header and in the `link` property of the response body. By default the page size is 10, but this can be changed by providing a value for the `size` query parameter. Sizes between 10 and 1000 are allowed.

### Requesting all collections

#### Request

```http
GET https://example.org/api/group_collections HTTP/1.1
```

#### Successful Response Status Code

`200 OK`

#### Successful response body

```json
{
    "hits": {
        "hits": [
            {
                "id": "5402d72b-b144-4891-aa8e-1038515d68f7",
                "created": "2024-01-01T00:00:00Z",
                "updated": "2024-01-01T00:00:00Z",
                "links": {
                    "self": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7",
                    "self_html": "https://example.org/communities/panda-group-collection",
                    "settings_html": "https://example.org/communities/panda-group-collection/settings",
                    "logo": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/logo",
                    "rename": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/rename",
                    "members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members",
                    "public_members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members/public",
                    "invitations": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/invitations",
                    "requests": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/requests",
                    "records": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/records"
                },
                "revision_id": 1,
                "slug": "panda-group-collection",
                "metadata": {
                    "title": "The Panda Group Collection",
                    "description": "This is a collection about pandas.",
                    "website": "https://example.org/pandas",
                    "organizations": [
                        {
                            "name": "Panda Research Institute",
                        }
                    ],
                    "size": 100,
                },
                "custom_fields": {
                    "kcr:commons_instance": "knowledgeCommons",
                    "kcr:commons_group_description": "This is a group for panda research.",
                    "kcr:commons_group_id": "12345",
                    "kcr:commons_group_name": "Panda Research Group",
                    "kcr:commons_group_visibility": "public",
                },
                "access": {
                    "visibility": "public",
                    "member_policy": "closed",
                    "record_policy": "open",
                    "review_policy": "open",
                }
            },
            ...
        ],
        "total": 100,
    },
    "links": {
        "self": "https://example.org/api/group_collections",
        "first": "https://example.org/api/group_collections?page=1",
        "last": "https://example.org/api/group_collections?page=10",
        "prev": "https://example.org/api/group_collections?page=1",
        "next": "https://example.org/api/group_collections?page=2",
    }
    "sortBy": "updated",
    "order": "ascending",
}
```

#### Successful Response Headers

| Header name | Header value |
| ------------|-------------- |
| Content-Type | `application/json` |
| Link | `<https://example.org/api/group_collections?page=1>; rel="first", <https://example.org/api/group_collections?page=10>; rel="last", <https://example.org/api/group_collections?page=1>; rel="prev", <https://example.org/api/group_collections?page=2>; rel="next"` |

### Requesting collections for a Commons instance

#### Request

```http
GET https://example.org/api/group_collections?commons_instance=knowledgeCommons HTTP/1.1
```

#### Successful response status code

`200 OK`

#### Successful Response Body:

```json
{
    "hits": {
        "hits": [
            {
                "id": "5402d72b-b144-4891-aa8e-1038515d68f7",
                "created": "2024-01-01T00:00:00Z",
                "updated": "2024-01-01T00:00:00Z",
                "links": {
                    "self": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7",
                    "self_html": "https://example.org/communities/panda-group-collection",
                    "settings_html": "https://example.org/communities/panda-group-collection/settings",
                    "logo": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/logo",
                    "rename": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/rename",
                    "members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members",
                    "public_members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members/public",
                    "invitations": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/invitations",
                    "requests": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/requests",
                    "records": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/records"
                },
                "revision_id": 1,
                "slug": "panda-group-collection",
                "metadata": {
                    "title": "The Panda Group Collection",
                    "description": "This is a collection about pandas.",
                    "website": "https://example.org/pandas",
                    "organizations": [
                        {
                            "name": "Panda Research Institute",
                        }
                    ],
                    "size": 100,
                },
                "custom_fields": {
                    "kcr:commons_instance": "knowledgeCommons",
                    "kcr:commons_group_description": "This is a group for panda research.",
                    "kcr:commons_group_id": "12345",
                    "kcr:commons_group_name": "Panda Research Group",
                    "kcr:commons_group_visibility": "public",
                },
                "access": {
                    "visibility": "public",
                    "member_policy": "closed",
                    "record_policy": "open",
                    "review_policy": "open",
                }
            },
            ...
        ],
        "total": 90,
    },
    "links": {
        "self": "https://example.org/api/group_collections?commons_instance=knowledgeCommons",
        "first": "https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=1",
        "last": "https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=9",
        "prev": "https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=1",
        "next": "https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=2",
    }
    "sortBy": "updated",
    "order": "ascending",
}
```

#### Successful response headers

| Header name | Header value |
| ------------|-------------- |
| Content-Type | `application/json` |
| Link | `<https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=1>; rel="first", <https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=9>; rel="last", <https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=1>; rel="prev", <https://example.org/api/group_collections?commons_instance=knowledgeCommons&page=2>; rel="next"` |


### Requesting collections for a specific group

#### Request

```http
GET https://example.org/api/group_collections?commons_instance=knowledgeCommons&commons_group_id=12345 HTTP/1.1
```

#### Successful response status code

`200 OK`

#### Successful Response Body:

```json
{
    "hits": {
        "hits": [
            {
                "id": "5402d72b-b144-4891-aa8e-1038515d68f7",
                "created": "2024-01-01T00:00:00Z",
                "updated": "2024-01-01T00:00:00Z",
                "links": {
                    "self": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7",
                    "self_html": "https://example.org/communities/panda-group-collection",
                    "settings_html": "https://example.org/communities/panda-group-collection/settings",
                    "logo": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/logo",
                    "rename": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/rename",
                    "members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members",
                    "public_members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members/public",
                    "invitations": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/invitations",
                    "requests": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/requests",
                    "records": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/records"
                },
                "revision_id": 1,
                "slug": "panda-group-collection",
                "metadata": {
                    "title": "The Panda Group Collection",
                    "description": "This is a collection about pandas.",
                    "website": "https://example.org/pandas",
                    "organizations": [
                        {
                            "name": "Panda Research Institute",
                        }
                    ],
                    "size": 2,
                },
                "custom_fields": {
                    "kcr:commons_instance": "knowledgeCommons",
                    "kcr:commons_group_description": "This is a group for panda research.",
                    "kcr:commons_group_id": "12345",
                    "kcr:commons_group_name": "Panda Research Group",
                    "kcr:commons_group_visibility": "public",
                },
                "access": {
                    "visibility": "public",
                    "member_policy": "closed",
                    "record_policy": "open",
                    "review_policy": "open",
                }
            },
            ...
        ],
        "total": 100,
    },
    "links": {
        "self": "https://example.org/api/group_collections",
        "first": "https://example.org/api/group_collections?page=1",
        "last": "https://example.org/api/group_collections?page=1",
        "prev": "https://example.org/api/group_collections?page=1",
        "next": "https://example.org/api/group_collections?page=1",
    }
    "sortBy": "updated",
    "order": "ascending",
}
```

#### Successful response headers

| Header name | Header value |
| ------------|-------------- |
| Content-Type | `application/json` |
| Link | `<https://example.org/api/group_collections?commons_instance=knowledgeCommons&commons_group_id=12345&page=1>; rel="first", <https://example.org/api/group_collections?commons_instance=knowledgeCommons&commons_group_id=12345&page=1>; rel="last", <https://example.org/api/group_collections?commons_instance=knowledgeCommons&commons_group_id=12345&page=1>; rel="prev", <https://example.org/api/group_collections?commons_instance=knowledgeCommons&commons_group_id=12345&page=1>; rel="next"` |

### Requesting a specific collection

#### Request

```http
GET https://example.org/api/group_collections/my-collection-slug HTTP/1.1
```

#### Successful Response Status Code

`200 OK`

#### Successful Response Body:

```json
{
    "id": "5402d72b-b144-4891-aa8e-1038515d68f7",
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z",
    "links": {
        "self": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7",
        "self_html": "https://example.org/communities/panda-group-collection",
        "settings_html": "https://example.org/communities/panda-group-collection/settings",
        "logo": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/logo",
        "rename": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/rename",
        "members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members",
        "public_members": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/members/public",
        "invitations": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/invitations",
        "requests": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/requests",
        "records": "https://example.org/api/communities/5402d72b-b144-4891-aa8e-1038515d68f7/records"
    },
    "revision_id": 1,
    "slug": "panda-group-collection",
    "metadata": {
        "title": "The Panda Group Collection",
        "description": "This is a collection about pandas.",
        "website": "https://example.org/pandas",
        "organizations": [
            {
                "name": "Panda Research Institute",
            }
        ],
        "size": 100,
    },
    "custom_fields": {
        "kcr:commons_instance": "knowledgeCommons",
        "kcr:commons_group_description": "This is a group for pandas research.",
        "kcr:commons_group_id": "12345",
        "kcr:commons_group_name": "Panda Research Group",
        "kcr:commons_group_visibility": "public",
    },
    "access": {
        "visibility": "public",
        "member_policy": "closed",
        "record_policy": "open",
        "review_policy": "open",
    }
}
```


## POST

A POST request to this endpoint creates a new collection in Invenio
owned by the specified Commons group. If the collection is successfully
created, the response status code will be 201 Created, and the response
body will be a JSON object containing the URL slug for the newly
created collection.

### Request

```http
POST https://example.org/api/group_collections HTTP/1.1
```

### Request body

```json
{
    "commons_instance": "knowledgeCommons",
    "commons_group_id": "12345",
    "commons_group_name": "Panda Research Group",
    "commons_group_visibility": "public",
}
```

### Successful response status code

`201 Created`

### Successful response body

```json
{
    "commons_group_id": "12345",
    "collection": "new-collection-slug"
}
```


## PATCH

A PATCH request to this endpoint modifies an existing collection in Invenio
by changing the Commons group to which it belongs. This is the *only*
modification that can be made to a collection via this endpoint. Other
modifications to Commons group metadata should be handled by signalling the Invenio webhook for commons group metadata updates. Modifications to
internal metadata or settings for the Invenio collection should be made
view the Invenio "communities" API or the collection settings UI.

Note that the collection memberships in Invenio will be automatically
transferred to the new Commons group. The corporate roles for the old
Commons group will be removed from the collection and corporate roles
for the new Commons group will be added to its membership with appropriate
permissions. But any individual memberships that have been granted through
the Invenio UI will be left unchanged. If the new collection administrators
wish to change these individual memberships, they will need to do so through
the Invenio UI.

### Request

```http
PATCH https://example.org/api/group_collections/my-collection-slug HTTP/1.1
```

### Successful request body

```json
{
    "commons_instance": "knowledgeCommons",
    "old_commons_group_id": "12345",
    "new_commons_group_id": "67890",
    "new_commons_group_name": "My Group",
    "new_commons_group_visibility": "public",
}
```

### Successful response status code

`200 OK`

### Successful response body

```json
{
    "collection": "my-collection-slug"
    "old_commons_group_id": "12345",
    "new_commons_group_id": "67890",
}
```

### Unsuccessful response codes

- 400 Bad Request: The request body is missing required fields or contains
    invalid data.
- 404 Not Found: The collection does not exist.
- 403 Forbidden: The request is not authorized to modify the collection.
- 304 Not Modified: The collection is already owned by the specified
    Commons group.

## DELETE

A DELETE request to this endpoint deletes a collection in Invenio
owned by the specified Commons group. If the collection is successfully
deleted, the response status code will be 204 No Content.

### Request

```http
DELETE https://example.org/api/group_collections/my-collection-slug HTTP/1.1
```

### Successful response status code

`202 Accepted`

### Unsuccessful response codes

- 404 Not Found: The collection does not exist.
- 403 Forbidden: The request is not authorized to delete the collection.

Logging
-------

The module will log each POST, PATCH, or DELETE request to the endpoint
in a dedicated log file, `logs/invenio-group-collections.log`.

Endpoint security
-----------------

The endpoint is secured by a token that must be obtained by the Commons
instance administrator from the Invenio instance administrator. The token
must be provided in the "Authorization" request header.

"""

# from flask import render_template
from flask import (
    Blueprint,
    jsonify,
    make_response,
    request,
    current_app as app,
)
from flask.views import MethodView
from invenio_accounts.models import UserIdentity
from invenio_queues.proxies import current_queues
from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    MethodNotAllowed,
    NotFound,
    # Unauthorized,
)
import os

from .utils import logger
from .signals import remote_data_updated


class IDPUpdateWebhook(MethodView):
    """
    View class providing methods for the remote-user-data webhook api endpoint.
    """

    init_every_request = False  # FIXME: is this right?

    def __init__(self):
        self.webhook_token = os.getenv("REMOTE_USER_DATA_WEBHOOK_TOKEN")
        self.logger = logger

    def post(self):
        """
        Handle POST requests to the user data webhook endpoint.

        These are requests from a remote IDP indicating that user or group
        data has been updated on the remote server.
        """
        self.logger.debug("****Received POST request to webhook endpoint")
        # headers = request.headers
        # bearer = headers.get("Authorization")
        # token = bearer.split()[1]
        # if token != self.webhook_token:
        #     print("Unauthorized")
        #     raise Unauthorized

        try:
            idp = request.json["idp"]
            events = []
            config = app.config["REMOTE_USER_DATA_API_ENDPOINTS"][idp]
            entity_types = config["entity_types"]
            bad_entity_types = []
            bad_events = []
            users = []
            bad_users = []
            groups = []
            bad_groups = []

            for e in request.json["updates"].keys():
                if e in entity_types.keys():
                    logger.debug(
                        f"{idp} Received {e} update signal: "
                        f"{request.json['updates'][e]}"
                    )
                    for u in request.json["updates"][e]:
                        if u["event"] in entity_types[e]["events"]:
                            if e == "users":
                                user_identity = UserIdentity.query.filter_by(
                                    id=u["id"], method=idp
                                ).one_or_none()
                                if user_identity is None:
                                    bad_users.append(u["id"])
                                    logger.error(
                                        f"Received update signal from {idp} "
                                        f"for unknown user: {u['id']}"
                                    )
                                else:
                                    users.append(u["id"])
                                    events.append(
                                        {
                                            "idp": idp,
                                            "entity_type": e,
                                            "event": u["event"],
                                            "id": u["id"],
                                        }
                                    )
                            elif e == "groups":
                                groups.append(u["id"])
                                events.append(
                                    {
                                        "idp": idp,
                                        "entity_type": e,
                                        "event": u["event"],
                                        "id": u["id"],
                                    }
                                )
                        else:
                            bad_events.append(u)
                            logger.error(
                                f"{idp} Received update signal for "
                                f"unknown event: {u}"
                            )
                else:
                    bad_entity_types.append(e)
                    logger.error(
                        f"{idp} Received update signal for unknown "
                        f"entity type: {e}"
                    )
                    logger.error(request.json)

            if len(events) > 0:
                current_queues.queues["user-data-updates"].publish(events)
                remote_data_updated.send(
                    app._get_current_object(), events=events
                )
                logger.debug(
                    f"Published {len(events)} events to queue and emitted"
                    " remote_data_updated signal"
                )
                logger.debug(events)
            else:
                if not users and bad_users or not groups and bad_groups:
                    entity_string = ""
                    if not users and bad_users:
                        entity_string += "users"
                    if not groups and bad_groups:
                        if entity_string:
                            entity_string += " and "
                        entity_string += "groups"
                    logger.error(
                        f"{idp} requested updates for {entity_string} that"
                        " do not exist"
                    )
                    logger.error(request.json["updates"])
                    raise NotFound
                elif not groups and bad_groups:
                    logger.error(
                        f"{idp} requested updates for groups that do not exist"
                    )
                    logger.error(request.json["updates"])
                    raise NotFound
                else:
                    logger.error(f"{idp} No valid events received")
                    logger.error(request.json["updates"])
                    raise BadRequest

            # return error message after handling signals that are
            # properly formed
            if len(bad_entity_types) > 0 or len(bad_events) > 0:
                # FIXME: raise better error, since request isn't
                # completely rejected
                raise BadRequest
        except KeyError:  # request is missing 'idp' or 'updates' keys
            logger.error(f"Received malformed signal: {request.json}")
            raise BadRequest

        return (
            jsonify(
                {"message": "Webhook notification accepted", "status": 202}
            ),
            202,
        )

    def get(self):
        return (
            jsonify({"message": "Webhook receiver is active", "status": 200}),
            200,
        )

    def put(self):
        raise MethodNotAllowed

    def delete(self):
        raise MethodNotAllowed


def create_api_blueprint(app):
    """Register blueprint on api app."""
    blueprint = Blueprint("invenio_remote_user_data", __name__)

    # routes = app.config.get("APP_RDM_ROUTES")

    blueprint.add_url_rule(
        "/webhooks/idp_data_update",
        view_func=IDPUpdateWebhook.as_view("ipd_update_webhook"),
    )

    # Register error handlers
    blueprint.register_error_handler(
        Forbidden,
        lambda e: make_response(
            jsonify({"error": "Forbidden", "status": 403}), 403
        ),
    )
    blueprint.register_error_handler(
        MethodNotAllowed,
        lambda e: make_response(
            jsonify({"message": "Method not allowed", "status": 405}), 405
        ),
    )

    return blueprint
