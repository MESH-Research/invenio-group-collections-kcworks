# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 MESH Research
#
# invenio-groups is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

import pytest
from flask import Flask
from invenio_celery import InvenioCelery
from invenio_db import InvenioDB
from invenio_i18n import InvenioI18N
# from invenio_groups import InvenioGroups
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


@pytest.fixture(scope="module")
def create_app(instance_path):
    """Application factory fixture for use with pytest-invenio."""

    def _create_app(**config):
        app_ = Flask(
            __name__,
            instance_path=instance_path,
        )
        app_.config.update(config)
        InvenioCelery(app_)
        InvenioDB(app_)
        # InvenioRecords(app_)
        InvenioI18N(app_)
        return app_

    return _create_app


@pytest.fixture(scope="module")
def testapp(base_app, database):
    """Application with just a database.

    Pytest-Invenio also initialises ES with the app fixture.
    """
    yield base_app