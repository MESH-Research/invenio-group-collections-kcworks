# invenio-groups

Social groups infrastructure for the InvenioRDM repository system.

## Installation

From your InvenioRDM instance directory:

    pipenv install invenio-groups

This will add the package to your Pipfile and install it in your InvenioRDM instance's virtual environment.

## Usage

The package will automatically provide the entry points for InvenioRDM to register the database models to store groups metadata.

### Versions

This repository follows [calendar versioning](https://calver.org/):

`2021.06.18` is both a valid semantic version and an indicator of the year-month corresponding to the loaded FAST terms.
