# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 MESH Research
#
# invenio-groups is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Pytest configuration for invenio-groups.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

import pytest
from flask_security.utils import hash_password
from invenio_access.models import ActionRoles, Role
from invenio_access.permissions import superuser_access, system_identity
from invenio_administration.permissions import administration_access_action
from invenio_app.factory import create_app as create_ui_api
from invenio_communities.proxies import current_communities
from invenio_communities.communities.records.api import Community
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.api import Vocabulary
import marshmallow as ma
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import DropConstraint, DropSequence, DropTable

pytest_plugins = ("celery.contrib.pytest",)


@pytest.fixture(scope="module")
def celery_config():
    """Override pytest-invenio fixture.

    TODO: Remove this fixture if you add Celery support.
    """
    return {}


test_config = {
    "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://invenio:invenio@localhost:5432/invenio",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "INVENIO_WTF_CSRF_ENABLED": False,
    "INVENIO_WTF_CSRF_METHODS": [],
    "APP_DEFAULT_SECURE_HEADERS": {
        "content_security_policy": {"default-src": []},
        "force_https": False,
    },
    "BROKER_URL": "amqp://guest:guest@localhost:5672//",
    "CELERY_CACHE_BACKEND": "memory",
    "CELERY_RESULT_BACKEND": "cache",
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS": True,
    "RATELIMIT_ENABLED": False,
    "SECRET_KEY": "test-secret-key",
    "SECURITY_PASSWORD_SALT": "test-secret-key",
    "TESTING": True,
}


@pytest.fixture(scope="module")
def app_config(app_config) -> dict:
    for k, v in test_config.items():
        app_config[k] = v
    return app_config


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"


@compiles(DropConstraint, "postgresql")
def _compile_drop_constraint(element, compiler, **kwargs):
    return compiler.visit_drop_constraint(element) + " CASCADE"


@compiles(DropSequence, "postgresql")
def _compile_drop_sequence(element, compiler, **kwargs):
    return compiler.visit_drop_sequence(element) + " CASCADE"


@pytest.fixture(scope="module")
def create_app():
    return create_ui_api


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

    Vocabulary.index.refresh()


@pytest.fixture(scope="function")
def sample_communities(app) -> list:

    try:
        current_communities.service.create(
            identity=system_identity,
            data={
                "access": {
                    "visibility": "public",
                    "member_policy": "open",
                    "record_policy": "open",
                },
                "slug": "community-1",
                "metadata": {
                    "title": "Community 1",
                    "description": "Community 1 description",
                    "type": {
                        "id": "event",
                    },
                    "curation_policy": "Curation policy",
                    "page": "Information for community 1",
                    "website": "https://community1.com",
                    "organizations": [
                        {
                            "name": "Organization 1",
                        }
                    ],
                },
            },
        )
        current_communities.service.create(
            identity=system_identity,
            data={
                "access": {
                    "visibility": "public",
                    "member_policy": "open",
                    "record_policy": "open",
                },
                "slug": "community-2",
                "metadata": {
                    "title": "Community 2",
                    "description": "Community 2 description",
                    "type": {
                        "id": "organization",
                    },
                    "curation_policy": "Curation policy",
                    "page": "Information for community 2",
                    "website": "https://community2.com",
                    "organizations": [
                        {
                            "name": "Organization 2",
                        }
                    ],
                },
            },
        )
        Community.index.refresh()
    except ma.exceptions.ValidationError:
        pass


@pytest.fixture(scope="module")
def testapp(app):
    """Application with just a database.

    Pytest-Invenio also initialises ES with the app fixture.
    """
    yield app


@pytest.fixture()
def users(UserFixture, testapp, db) -> list:
    """Create example user."""
    # user1 = UserFixture(
    #     email="scottia4@msu.edu",
    #     password="password"
    # )
    # user1.create(app, db)
    # user2 = UserFixture(
    #     email="scottianw@gmail.com",
    #     password="password"
    # )
    # user2.create(app, db)
    with db.session.begin_nested():
        datastore = testapp.extensions["security"].datastore
        user1 = datastore.create_user(
            email="info@inveniosoftware.org",
            password=hash_password("password"),
            active=True,
        )
        user2 = datastore.create_user(
            email="ser-testalot@inveniosoftware.org",
            password=hash_password("beetlesmasher"),
            active=True,
        )

    db.session.commit()
    return [user1, user2]


@pytest.fixture()
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
    u = UserFixture(
        email="admin@inveniosoftware.org",
        password="admin",
    )
    u.create(app, db)

    datastore = app.extensions["security"].datastore
    _, role = datastore._prepare_role_modify_args(
        u.user, "administration-access"
    )

    datastore.add_role_to_user(u.user, role)
    db.session.commit()
    return u


@pytest.fixture()
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


@pytest.fixture()
def superuser_identity(admin, superuser_role_need):
    """Superuser identity fixture."""
    identity = admin.identity
    identity.provides.add(superuser_role_need)
    return identity
