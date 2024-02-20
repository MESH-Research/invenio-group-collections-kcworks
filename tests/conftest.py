# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 MESH Research
#
# invenio-groups is free software; you can redistribute it and/or # modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

import pytest
from flask import Flask
from flask_security import Security
from flask_security.utils import hash_password
from invenio_access import InvenioAccess
from invenio_access.models import ActionRoles, Role
from invenio_access.permissions import superuser_access, system_identity
from invenio_administration.permissions import administration_access_action
from invenio_app.factory import create_api
from invenio_celery import InvenioCelery
from invenio_db import InvenioDB
from invenio_records import InvenioRecords
from invenio_i18n import InvenioI18N
from invenio_groups.ext import InvenioGroups
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_search import InvenioSearch
from pytest_invenio.fixtures import UserFixture
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import DropConstraint, DropSequence, DropTable

pytest_plugins = ("celery.contrib.pytest",)

@pytest.fixture(scope='module')
def celery_config():
    """Override pytest-invenio fixture.

    TODO: Remove this fixture if you add Celery support.
    """
    return {}

test_config = {

    'SQLALCHEMY_DATABASE_URI': "postgresql+psycopg2://invenio:invenio@localhost:5432/invenio",
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'INVENIO_WTF_CSRF_ENABLED': False,
    'INVENIO_WTF_CSRF_METHODS': [],
    'APP_DEFAULT_SECURE_HEADERS':
        {'content_security_policy': {'default-src': []},
                                     'force_https': False},
    'BROKER_URL': 'amqp://guest:guest@localhost:5672//',
    'CELERY_CACHE_BACKEND': 'memory',
    'CELERY_RESULT_BACKEND': 'cache',
    'CELERY_TASK_ALWAYS_EAGER': True,
    'CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS': True,
    'RATELIMIT_ENABLED': False,
    'SECRET_KEY': 'test-secret-key',
    'SECURITY_PASSWORD_SALT': 'test-secret-key',
    'TESTING': True,
}


@pytest.fixture(scope='module')
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


# @pytest.fixture(scope="module")
# def create_app(instance_path):
#     """Application factory fixture for use with pytest-invenio."""

#     def _create_app(**config):
#         app_ = Flask(
#             __name__,
#             instance_path=instance_path,
#         )
#         app_.config.update(config)
#         InvenioCelery(app_)
#         InvenioDB(app_)
#         InvenioSearch(app_)
#         InvenioRecords(app_)
#         Security(app_)
#         InvenioAccess(app_)
#         InvenioJSONSchemas(app_)
#         InvenioGroups(app_)
#         InvenioI18N(app_)
#         return app_

#     return _create_app

@pytest.fixture(scope="module")
def create_app():
    return create_api

@pytest.fixture(scope="module")
def testapp(base_app, database):
    """Application with just a database.

    Pytest-Invenio also initialises ES with the app fixture.
    """
    InvenioGroups(base_app)
    yield base_app


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

    action_role = ActionRoles.create(action=administration_access_action, role=role)
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
    _, role = datastore._prepare_role_modify_args(u.user, "administration-access")

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