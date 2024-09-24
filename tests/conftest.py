# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Pytest configuration for invenio-group-collections-kcworks.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

# from traceback import format_exc
import traceback
from invenio_accounts import current_accounts
import pytest
from invenio_access.models import ActionRoles, Role
from invenio_access.permissions import superuser_access, system_identity
from invenio_administration.permissions import administration_access_action
from invenio_app.factory import create_api
from invenio_communities.proxies import current_communities
from invenio_communities.communities.records.api import Community
from invenio_oauth2server.models import Token
from invenio_records_resources.services.custom_fields import TextCF
from invenio_records_resources.services.custom_fields.errors import (
    CustomFieldsException,
)
from invenio_records_resources.services.custom_fields.mappings import Mapping
from invenio_records_resources.services.custom_fields.validate import (
    validate_custom_fields,
)
from invenio_search import current_search_client
from invenio_search.engine import dsl
from invenio_search.engine import search as search_engine
from invenio_search.utils import build_alias_name
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.api import Vocabulary
import marshmallow as ma

pytest_plugins = ("celery.contrib.pytest",)


@pytest.fixture(scope="module")
def communities_service(app):
    return current_communities.service


test_config = {
    "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://"
    "invenio:invenio@localhost:5432/invenio",
    "INVENIO_WTF_CSRF_ENABLED": False,
    "INVENIO_WTF_CSRF_METHODS": [],
    "APP_DEFAULT_SECURE_HEADERS": {
        "content_security_policy": {"default-src": []},
        "force_https": False,
    },
    "BROKER_URL": "amqp://guest:guest@localhost:5672//",
    "CELERY_BROKER_URL": "amqp://guest:guest@localhost:5672//",
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS": True,
    "RATELIMIT_ENABLED": False,
    "SECRET_KEY": "test-secret-key",
    "SECURITY_PASSWORD_SALT": "test-secret-key",
    "TESTING": True,
    "RECORDS_REFRESOLVER_CLS": "invenio_records.resolver.InvenioRefResolver",
    "RECORDS_REFRESOLVER_STORE": (
        "invenio_jsonschemas.proxies.current_refresolver_store"
    ),
    # Variable not used. We set it to silent warnings
    "JSONSCHEMAS_HOST": "not-used",
    # Define files storage class list
    "FILES_REST_STORAGE_CLASS_LIST": {
        "L": "Local",
        "F": "Fetch",
        "R": "Remote",
    },
    "FILES_REST_DEFAULT_STORAGE_CLASS": "L",
}

test_config["SSO_SAML_IDPS"] = {
    # name your authentication provider
    "knowledgeCommons": {
        # Basic info
        "title": "Knowledge Commons",
        "description": "Knowledge Commons Authentication Service",
        # "icon": "",
        # path to the file i.e. "./saml/sp.crt"
        "sp_cert_file": "./docker/nginx/samlCertificate.crt",
        # path to the file i.e. "./saml/sp.key"
        "sp_key_file": "./docker/nginx/samlPrivateKey.key",
        "settings": {
            # If strict is True, then the Python Toolkit will reject unsigned
            # or unencrypted messages if it expects them to be signed
            # or encrypted.
            # Also it will reject the messages if the SAML standard is
            # not strictly
            # followed. Destination, NameId, Conditions ... are validated too.
            "strict": False,
            # Enable debug mode (outputs errors).
            # TODO: change before production
            "debug": True,
            # Service Provider Data that we are deploying.
            "sp": {
                # NOTE: Assertion consumer service is https://localhost/saml/
                # authorized/knowledgeCommons
                # NOTE: entityId for the dev SP is
                # https://localhost/saml/metadata/knowledgeCommons
                # NOTE: entityId for the staging SP is
                # https://invenio-dev.hcommons-staging.org/saml/idp
                # Specifies the constraints on the name identifier to be used
                # to represent the requested subject.
                # Take a look on https://github.com/onelogin/python-saml/
                # blob/master/src/onelogin/saml2/constants.py
                # to see the NameIdFormat that are supported.
                "NameIDFormat": (
                    "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
                ),
            },
            # Identity Provider Data that we want connected with our SP.
            "idp": {
                # Identifier of the IdP entity  (must be a URI)
                "entityId": "https://proxy.hcommons-dev.org/idp",
                # SSO endpoint info of the IdP. (Authentication
                # Request protocol)
                "singleSignOnService": {
                    # URL Target of the IdP where the Authentication
                    # Request Message will be sent.
                    "url": "https://proxy.hcommons-dev.org/Saml2/sso/redirect",
                    # SAML protocol binding to be used when returning the
                    # <Response> message. OneLogin Toolkit supports
                    # the HTTP-Redirect binding
                    # only for this endpoint.
                    "binding": (
                        "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                    ),
                },
                # SLO endpoint info of the IdP.
                "singleLogoutService": {
                    # URL Location where the <LogoutRequest> from the IdP
                    # will be sent (IdP-initiated logout)
                    "url": "https://localhost/saml/slo/knowledgeCommons",
                    # SAML protocol binding to be used when returning
                    # the <Response> message. OneLogin Toolkit supports
                    # the HTTP-Redirect binding
                    # only for this endpoint.
                    "binding": (
                        "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                    ),
                },
                # Public X.509 certificate of the IdP
                "x509cert": (
                    "MIIELTCCApWgAwIBAgIJAPeDxhrttBXNMA0GCSqGSIb3DQEBCwUAMCExHzAdBgNVBAMTFnByb3h5Lmhjb21tb25zLWRldi5vcmcwHhcNMTcxMTAxMTc0NTE3WhcNMjcxMDMwMTc0NTE3WjAhMR8wHQYDVQQDExZwcm94eS5oY29tbW9ucy1kZXYub3JnMIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA0d6ycqcxviv946IzS7ZobCK0XAsrwHvcKo65hWkOZsxYBTRvjKITSpKv4TGyVG4leI0Ifthz7o3QAA4IKkkgY15kYO5AhJc9pVa+11vG0DM58qO6yraQRM4U/71AgDEmEZXsUblf3TCkN5w351G26jNwgax+aWNuwzX5EDS5farOhruGG2FwVYEOEHOtWSOKBR8duq1O/yY9OKMhIc2kmh9R"  # noqa: E501
                    " m1594qTzZbxNXjyCY+LU/GZbYQP+WlbjM/dHflK5Y2WexyT942xHYnesvPnzGvEMB4g685Yyjl+9xz+AE41sifKYy03m7GgkimXNxQ2SnGZ4Rtj+3DlDC9S/dB2CRJd2uaTwgxEEK/zJJ1K2TFRfDH/wxCW5DwI3n8BMglc8TPZ33FDqNgZPwPDl92/shwNIU3sFM/lmDtLm/4XeKZjOZYa+WCVC71tnFYDltK1//oAqFSVRF0WT6+dcnjXxJSdRrQo+C1gWI+aXJzmDmhp8WBN2q7nUGapJYSu0a5yXAgMBAAGjaDBmMEUGA1UdEQQ+MDyCFnByb3h5Lmhjb21tb25zLWRldi5vcmeGImh0dHBzOi8vcHJveHkuaGNvbW1vbnMtZGV2Lm9yZy9pZHAwHQYDVR0OBBYEFDLkys52MyePCpr5IN2ybhgIosmlMA0GCSqGSIb3DQEBCwUAA4IBgQDOuUnSwfru5uNorAISo5QEVUi3UrholF0RPFFvM6P63MOpWZwdFQYKjY1eaaE+X++AZ1FkHQv/esy7F0FRWiyU3LHUX3Yzuttb7vj7mw5D6IYuSIG1/0Edj/eSpnOs+6MQUUpfaFi+A0C9Smng6L1kj3SOlePprJdwfIdGG/6oiDaF1bhoWs/eidouzMLMKiGY6KzmaT8fInST1BGMdm4+zqNvwd1FuifDOvVQqqtl"  # noqa: E501
                    " q2og0arTXG01YyCvU+NJT/6KjLDZf1bSmDWAPQ51Fc4fpkeOj+aG0DfwdutO2SNkdDDdD/m7pnepxv2u8jqSKyYKdrzLd0lJPrqH8YV4AYmyJ1UortJXFoTsGSbPv0fw"  # noqa: E501
                    " qM1b1JAKsPMP22xmp2i4BcYOT1jZ+R+RXmMNK+fUSXAmSkhk/8h6CMgmU4ldBj5jtyn/M4GrGesMU1sIgidoCj/5F3jQlswz0eoaX3LyWQkDZbUbIm6Vz4h3GFwwlky8c5RbLEmwlolP+zSzoq4T/tw="  # noqa: E501
                ),
            },
            # Security settings
            # more on https://github.com/onelogin/python-saml
            "security": {
                "authnRequestsSigned": False,
                "failOnAuthnContextMismatch": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "metadataCacheDuration": None,
                "metadataValidUntil": None,
                "nameIdEncrypted": False,
                "requestedAuthnContext": False,
                "requestedAuthnContextComparison": "exact",
                "signMetadata": False,
                "signatureAlgorithm": (
                    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
                ),
                "wantAssertionsEncrypted": False,
                "wantAssertionsSigned": False,
                "wantAttributeStatement": False,
                "wantMessagesSigned": False,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            },
        },
        # Account Mapping
        "mappings": {
            "email": "urn:oid:0.9.2342.19200300.100.1.3",  # "mail"
            # "name": "urn:oid:2.5.4.3",  # "cn"
            "name": "urn:oid:2.5.4.42",  # "givenName"
            "surname": "urn:oid:2.5.4.4",  # "sn"
            "external_id": (
                "urn:oid:2.16.840.1.113730.3.1.3"
            ),  # "employeeNumber"
        },  # FIXME: new entity id url, assertion consumer service url,
        # certificate
        # "title", 'urn:oid:2.5.4.12': ['Hc Developer'],
        # 'urn:oid:2.16.840.1.113730.3.1.3': ['iscott'],
        # 'urn:oid:0.9.2342.19200300.100.1.1':
        #   ['100103028069838784737+google.com@commons.mla.org'],
        # "isMemberOf", 'urn:oid:1.3.6.1.4.1.5923.1.5.1.1':
        #   ['CO:COU:HC:members:active'],
        # 'urn:oid:1.3.6.1.4.1.49574.110.13':
        #   ['https://google-gateway.hcommons-dev.org/idp/shibboleth'],
        # 'urn:oid:1.3.6.1.4.1.49574.110.10': ['Google login'],
        # 'urn:oid:1.3.6.1.4.1.49574.110.11': ['Humanities Commons'],
        # 'urn:oid:1.3.6.1.4.1.49574.110.12': ['Humanities Commons']}
        # Inject your remote_app to handler
        # Note: keep in mind the string should match
        # given name for authentication provider
        # NOTE: commented out to avoid import:
        # "acs_handler": acs_handler_factory("knowledgeCommons"),
        # Automatically set `confirmed_at` for users upon
        # registration, when using the default `acs_handler`
        "auto_confirm": True,
    }
}

# FIXME: provide proper namespace url
test_config["COMMUNITIES_NAMESPACES"] = {
    "kcr": "https://invenio-dev.hcommons-staging.org/terms/"
}

test_config["COMMUNITIES_CUSTOM_FIELDS"] = [
    TextCF(name="kcr:commons_instance"),
    TextCF(name="kcr:commons_group_id"),
    TextCF(name="kcr:commons_group_name"),
    TextCF(name="kcr:commons_group_description"),
    TextCF(name="kcr:commons_group_visibility"),
]

test_config["COMMUNITIES_CUSTOM_FIELDS_UI"] = [
    {
        "section": "Linked Commons Group",
        "hidden": False,
        "description": (
            "Information about a Commons group that owns the collection"
        ),
        "fields": [
            {
                "field": "kcr:commons_group_name",
                "ui_widget": "Input",
                "props": {
                    "label": "Commons Group Name",
                    "placeholder": "",
                    "icon": "",
                    "description": ("Name of the Commons group."),
                    "disabled": True,
                },
            },
            {
                "field": "kcr:commons_group_id",
                "ui_widget": "Input",
                "props": {
                    "label": "Commons Group ID",
                    "placeholder": "",
                    "icon": "",
                    "description": ("ID of the Commons group"),
                    "disabled": True,
                },
            },
            {
                "field": "kcr:commons_instance",
                "ui_widget": "Input",
                "props": {
                    "label": "Commons Instance",
                    "placeholder": "",
                    "icon": "",
                    "description": (
                        "The Commons to which the group belongs (e.g., "
                        "STEMEd+ Commons, MLA Commons, Humanities Commons)"
                    ),
                    "disabled": True,
                },
            },
            {
                "field": "kcr:commons_group_description",
                "ui_widget": "Input",
                "props": {
                    "label": "Commons Group Description",
                    "placeholder": "",
                    "icon": "",
                    "description": ("Description of the Commons group."),
                    "disabled": True,
                },
            },
            {
                "field": "kcr:commons_group_visibility",
                "ui_widget": "Input",
                "props": {
                    "label": "Commons Group Visibility",
                    "placeholder": "",
                    "icon": "",
                    "description": ("Visibility of the Commons group."),
                    "disabled": True,
                },
            },
        ],
    }
]


# @pytest.fixture(scope="session")
# def broker_uri():
#     yield "amqp://guest:guest@localhost:5672//"


@pytest.fixture(scope="session")
def celery_config(celery_config):
    # celery_config["broker_url"] = broker_uri
    celery_config["broker_url"] = "amqp://guest:guest@localhost:5672//"
    return celery_config


@pytest.fixture(scope="module")
def app_config(app_config) -> dict:
    for k, v in test_config.items():
        app_config[k] = v
    return app_config


@pytest.fixture(scope="module")
def create_app():
    return create_api


@pytest.fixture(scope="module")
def community_type_type(app):
    """Resource type vocabulary type."""
    return vocabulary_service.create_type(
        system_identity, "communitytypes", "comtyp"
    )


@pytest.fixture(scope="module")
def community_type_v(app, community_type_type):
    """Community type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "organization",
            "title": {"en": "Organization"},
            "type": "communitytypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "event",
            "title": {"en": "Event"},
            "type": "communitytypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "topic",
            "title": {"en": "Topic"},
            "type": "communitytypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "project",
            "title": {"en": "Project"},
            "type": "communitytypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "group",
            "title": {"en": "Group"},
            "type": "communitytypes",
        },
    )

    Vocabulary.index.refresh()


def create_communities_custom_fields(app):
    """Creates one or all custom fields for communities.

    $ invenio custom-fields communities create [field].
    """
    available_fields = app.config.get("COMMUNITIES_CUSTOM_FIELDS")
    namespaces = set(app.config.get("COMMUNITIES_NAMESPACES").keys())
    try:
        validate_custom_fields(
            given_fields=None,
            available_fields=available_fields,
            namespaces=namespaces,
        )
    except CustomFieldsException as e:
        print(f"Custom fields configuration is not valid. {e.description}")
    # multiple=True makes it an iterable
    properties = Mapping.properties_for_fields(None, available_fields)

    try:
        communities_index = dsl.Index(
            build_alias_name(
                current_communities.service.config.record_cls.index._name
            ),
            using=current_search_client,
        )
        communities_index.put_mapping(body={"properties": properties})
    except search_engine.RequestError as e:
        print("An error occured while creating custom fields.")
        print(e.info["error"]["reason"])


@pytest.fixture(scope="function")
def custom_fields(app):
    create_communities_custom_fields(app)


@pytest.fixture(scope="function")
def sample_communities(app, db):
    create_communities_custom_fields(app)

    def create_communities(app, communities_service) -> None:
        communities = communities_service.read_all(
            identity=system_identity, fields=["slug"]
        )
        if communities.total > 0:
            print("Communities already exist.")
            return
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
                    "181920",
                    "MSU Group 3",
                    "MSU Community 3",
                ),
                (
                    "212223",
                    "MSU Group 4",
                    "MSU Community 4",
                ),
            ],
        }
        try:
            for instance in communities_data.keys():
                for c in communities_data[instance]:
                    slug = c[2].lower().replace("-", "").replace(" ", "")
                    rec_data = {
                        "access": {
                            "visibility": "public",
                            "member_policy": "open",
                            "record_policy": "open",
                            "review_policy": "closed",
                            "members_visibility": "public",
                        },
                        "slug": c[2].lower().replace(" ", "-"),
                        "metadata": {
                            "title": c[2],
                            "description": c[2] + " description",
                            "type": {
                                "id": "event",
                            },
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
                            "kcr:commons_group_description": (
                                f"{c[1]} description"
                            ),
                            "kcr:commons_group_visibility": "public",
                        },
                    }
                    rec = communities_service.create(
                        identity=system_identity, data=rec_data
                    )
                    assert rec["metadata"]["title"] == c[2]
            Community.index.refresh()
        except ma.exceptions.ValidationError:
            print("Error creating communities.")
            print(traceback.format_exc())
            pass

    return create_communities


# @pytest.fixture(scope="module")
# def testapp(app):
#     """Application with just a database.

#     Pytest-Invenio also initialises ES with the app fixture.
#     """
#     yield app


@pytest.fixture(scope="function")
def user_factory(app, db, UserFixture):
    def make_user(
        email="info@inveniosoftware.org", password="password", **kwargs
    ):
        # with db.session.begin_nested():
        #     datastore = app.extensions["security"].datastore
        #     user1 = datastore.create_user(
        #         email=email,
        #         password=hash_password(password),
        #         active=True,
        #         **kwargs,
        #     )
        # db.session.commit()
        u = UserFixture(
            email=email,
            password=password,
        )
        u.create(app, db)

        return u

    return make_user


@pytest.fixture(scope="function")
def admin_role_need(db):
    """Store 1 role with 'superuser-access' ActionNeed.

    WHY: This is needed because expansion of ActionNeed is
         done on the basis of a User/Role being associated with that Need.
         If no User/Role is associated with that Need (in the DB), the
         permission is expanded to an empty list.
    """
    role = Role(name="administration-access")
    db.session.add(role)

    action_role = ActionRoles.create(
        action=administration_access_action, role=role
    )
    db.session.add(action_role)

    db.session.commit()
    return action_role.need


@pytest.fixture()
def admin(UserFixture, app, db, admin_role_need):
    """Admin user for requests."""

    email = "admin@inveniosoftware.org"
    password = "admin"
    u = UserFixture(
        email=email,
        password=password,
    )
    u.create(app, db)

    current_accounts.datastore.find_or_create_role("admin")

    current_accounts.datastore.find_or_create_role("administrator")

    current_accounts.datastore.find_or_create_role("group-collections-owner")

    current_accounts.datastore.add_role_to_user(u.user, "admin")

    current_accounts.datastore.add_role_to_user(
        u.user, "administration-access"
    )
    current_accounts.datastore.add_role_to_user(
        u.user, "group-collections-owner"
    )

    u.allowed_token = Token.create_personal(
        "webhook", u.id, scopes=[]  # , is_internal=False
    ).access_token

    current_accounts.datastore.commit()

    return u


@pytest.fixture(scope="function")
def superuser_role_need(db):
    """Store 1 role with 'superuser-access' ActionNeed.

    WHY: This is needed because expansion of ActionNeed is
         done on the basis of a User/Role being associated with that Need.
         If no User/Role is associated with that Need (in the DB), the
         permission is expanded to an empty list.
    """
    role = Role(name="superuser-access")
    db.session.add(role)

    action_role = ActionRoles.create(action=superuser_access, role=role)
    db.session.add(action_role)

    db.session.commit()

    return action_role.need


@pytest.fixture(scope="function")
def superuser_identity(admin_factory, superuser_role_need):
    """Superuser identity fixture."""
    admin = admin_factory()
    identity = admin.identity
    identity.provides.add(superuser_role_need)
    return identity


@pytest.fixture(scope="function")
def not_found_response_body():
    return {
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


@pytest.fixture(scope="function")
def sample_community1(app, communities_service, user_factory):
    sample1 = {
        "api_response": {
            "id": "1004290",
            "name": "The Inklings",
            "url": "https://hcommons-dev.org/groups/the-inklings/",
            "visibility": "public",
            "description": "For scholars interested in J.R.R. Tolkien, C. S. Lewis, Charles Williams, and other writers associated with the Inklings.",  # noqa
            "avatar": "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",  # noqa
            "groupblog": "",
            "upload_roles": ["member", "moderator", "administrator"],
            "moderate_roles": ["moderator", "administrator"],
        },
        "expected_record": {
            # "id": "55d2af81-fa4e-4ac0-866f-a8d99c333c6d",
            # "created": "2024-05-03T23:48:46.312644+00:00",
            # "updated": "2024-05-03T23:48:46.536669+00:00",
            # "links": {
            #     "featured": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/featured",  # noqa
            #     "self": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d",  # noqa
            #     "self_html": "https://127.0.0.1:5000/communities/knowledgeCommons---1004290",  # noqa
            #     "settings_html": "https://127.0.0.1:5000/communities/knowledgeCommons---1004290/settings",  # noqa
            #     "logo": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/logo",  # noqa
            #     "rename": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/rename",  # noqa
            #     "members": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/members",  # noqa
            #     "public_members": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/members/public",  # noqa
            #     "invitations": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/invitations",  # noqa
            #     "requests": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/requests",  # noqa
            #     "records": "https://127.0.0.1:5000/api/communities/55d2af81-fa4e-4ac0-866f-a8d99c333c6d/records",  # noqa # },
            "slug": "the-inklings",
            "metadata": {
                "title": "The Inklings",
                "description": "A collection managed by The Inklings, a Knowledge Commons group",  # noqa
                "curation_policy": "",
                "page": "This is a collection of works curated by The Inklings, a Knowledge Commons group",  # noqa
                "website": "https://hcommons-dev.org/groups/the-inklings/",  # noqa
                "organizations": [
                    {"name": "The Inklings"},
                    {"name": "Knowledge Commons"},
                ],
            },
            "access": {
                "visibility": "restricted",
                "members_visibility": "public",
                "member_policy": "closed",
                "record_policy": "closed",
                "review_policy": "closed",
            },
            "custom_fields": {
                "kcr:commons_instance": "knowledgeCommons",
                "kcr:commons_group_id": "1004290",
                "kcr:commons_group_name": "The Inklings",
                "kcr:commons_group_description": "For scholars interested in J.R.R. Tolkien, C. S. Lewis, Charles Williams, and other writers associated with the Inklings.",  # noqa
                "kcr:commons_group_visibility": "public",
            },
            "deletion_status": {
                "is_deleted": False,
                "status": "P",
            },
            "children": {"allow": False},
        },
    }
    sample1["creation_metadata"] = {
        k: v
        for k, v in sample1["expected_record"].items()
        if k
        not in [
            "id",
            "created",
            "updated",
            "links",
            "deletion_status",
            "children",
        ]
    }

    def create_sample1():
        rec = communities_service.create(
            identity=system_identity, data=sample1["creation_metadata"]
        )

        for r in [
            "knowledgeCommons---1004290|admin",
            "knowledgeCommons---1004290|moderator",
            "knowledgeCommons---1004290|member",
            "knowledgeCommons---1004290|administrator",
        ]:
            current_accounts.datastore.find_or_create_role(r)

        myuser = user_factory()

        current_accounts.datastore.add_role_to_user(
            myuser.user, "knowledgeCommons---1004290|admin"
        )

        communities_service.members.add(
            system_identity,
            rec.id,
            data={
                "members": [
                    {
                        "id": "knowledgeCommons---1004290|admin",
                        "type": "group",
                    }
                ],
                "role": "manager",
            },
        )

        Community.index.refresh()

        return rec

    sample1["create_func"] = create_sample1

    return sample1
