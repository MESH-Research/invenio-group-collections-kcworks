# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

import click

"""
A command line interface for administering social group collections
in InvenioRDM.

"""


@click.group()
def cli():
    pass


if __name__ == "__main__":
    cli()
