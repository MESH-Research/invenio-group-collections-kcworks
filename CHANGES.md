# Changes

## Version 1.1 (2026-11-26)

- **Feature**: associate or transfer existing group collection
  - Until now it has only been possible to link a new community to a KC group.
    This updat3e introduces the ability to associate existing communities with
    KC groups and to transfer that association between groups. These actions are
    exposed through new API endpoints and protected by a combination of OAuth
    scopes, KC group role, KCWorks role, and in some cases role in an existing
    KCWorks collection.
  - The version also includes tests for the new functionality, as well as a
    reorganization of the package's test suite. It can now run either
    stand-alone or as part of the central KCWorks test suite (as with our other
    extension submodules.)

## Version 1.0

- Introduced improved role-based authentication for service methods and oauth
  token scopes for view access control.
