# U6 · Accounts and roles · requirements

R-050 to R-052 moved here verbatim from the design document. R-601 to R-604 are this unit's own.

```
R-050  THE system SHALL create an account only through a valid, unexpired, unused invitation issued by an admin or curator.
       Gate: tests/accounts/test_accounts.py::test_registration_requires_invitation

R-051  WHERE a mail sender credential is configured, THE system SHALL mail invitations and password-reset links through it; otherwise it SHALL show the link to the issuing admin only.
       Gate: tests/accounts/test_accounts.py::test_mail_adapter_against_local_sink

R-052  THE API SHALL enforce roles: visitor reads, contributor submits, identifier identifies, curator moderates and overrides placement, admin manages invitations.
       Gate: tests/accounts/test_roles.py::test_role_matrix

R-601  WHEN several registrations use one invitation at the same time, THE system SHALL create exactly one account.
       Gate: tests/accounts/test_accounts.py::test_one_link_one_account_under_a_race

R-602  THE API SHALL NOT expose a registration route that works without an invitation.
       Gate: tests/accounts/test_accounts.py::test_no_open_registration_route

R-603  IF a state-changing request comes from a browser page of another origin, THEN THE API SHALL refuse it, while reads stay open to any origin.
       Gate: tests/accounts/test_roles.py::test_cross_site_writes_are_refused

R-604  WHEN an account signs out, THE session SHALL stop working at once.
       Gate: tests/accounts/test_roles.py::test_sessions_end_at_sign_out
```
