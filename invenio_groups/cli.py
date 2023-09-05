# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 MESH Research
#
# invenio-groups is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

import click

"""
A Script and command line interface for administering social groups in InvenioRDM.

"""

@click.group()
def cli():
    pass


if __name__ == "__main__":
    cli()