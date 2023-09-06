# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Create invenio-groups table"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '737496a37317'
down_revision = None
branch_labels = ('invenio_groups',)
depends_on = None


def upgrade():
    """Upgrade database."""
    op.create_table(
        "groups_metadata",
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("id", sqlalchemy_utils.types.uuid.UUIDType(), nullable=False),
        sa.Column(
            "json",
            sqlalchemy_utils.JSONType().with_variant(
                sa.dialects.postgresql.JSON(none_as_null=True),
                "postgresql",
            ),
            nullable=True,
        ),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    """Downgrade database."""
    op.drop_table("groups_metadata")
