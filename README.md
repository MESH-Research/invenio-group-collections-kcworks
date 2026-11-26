# Invenio Group Collections for Knowledge Commons Works

Version 1.0.0

Copyright 2024 Mesh Research Contributors: Ian Scott

The package provides integration between Knowledge Commons groups and InvenioRDM
collections (communities). It exposes a `group_collections` API endpoint that
can be used for automatic creation of an InvenioRDM record collection linked to
a group on a remote service. This package is intended for use with the Knowledge
Commons Works instance of InvenioRDM, although it could be customized to work
with other instances. If there is interest in using this package with other
instances, please contact the package maintainer to discuss how the package
could be updated to work for your use case.

This package is also intended to be used in conjunction with the
`invenio_remote_user_data_kcworks` package, which provides a similar integration
between group and user metadata from a remote service and InvenioRDM.

Updates to external apis (like a search index) for group collection events is
not handled in this package but rather in the `invenio_remote_api_provisioner`
package. Updates to Commons group metadata in a linked Invenio collection are
handled by the `invenio_remote_user_data_kcworks` package.

(Note: The Knowledge Commons Works instance of InvenioRDM uses the term
"collection" in place of the default term "community" employed in standard
InvenioRDM installations.)

## Installation

From your InvenioRDM instance directory:

```shell
    pipenv install invenio-group-collections-kcworks
```

This will add the package to your Pipfile and install it in your InvenioRDM
instance's virtual environment.

## Documentation

Operator and API documentation for this package lives in the Knowledge Commons
Works docs (not duplicated here):

- Docs home:
  https://mesh-research.github.io/knowledge-commons-works/
- Group Collections API (create, read, associate, transfer, delete):
  https://mesh-research.github.io/knowledge-commons-works/reference/api.html#group-collections-api
- Admin how-to (associating and transferring group collections):
  https://mesh-research.github.io/knowledge-commons-works/admin_guide/group_collections.html

## Logging

The module will log each POST, PATCH, or DELETE request to the
`group_collections` endpoint (as well as any errors) in a dedicated log file,
`logs/invenio-group-collections-kcworks.log`.

## Developing this package

### Versioning

This repository follows [semantic versioning](https://semver.org/).

#### Version history

The version history for this package is available in the
[CHANGES.md](./CHANGES.md) file. If you make changes to the code that prompt a
version change, you must also update the [CHANGES.md](./CHANGES.md) file to
indicate the new version number and the changes made to the code.

#### Updating the version number

This project uses the [bumpver](https://pypi.org/project/bumpver/) utility to
manage versioning.

To update the version number, run the following command:

```bash
bumpver update --<part of version to update>
```

where `<part of version to update>` is one of `major`, `minor`, `patch`, or
`tag-num`.

### Dependencies

At present this package has no dependencies on other packages that are not
available in the Python Package Index and installable via pip.

**NOTE:** The `invenio-communities` package has currently been forked for use in
KCWorks and is not available on the Python Package Index. The fork is available
at
[MESH-Research/invenio-communities](https://github.com/MESH-Research/invenio-communities).
The fork is currently included in the `dependencies` subdirectory of this
repository, but is not presently being used because the vanilla version of
`invenio-communities` is currently compatible with
`invenio-group-collections-kcworks`. This may change in the future.

### Running tests

```bash
bash run-tests.sh
```
