# U6 · Accounts and roles · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | `user`, `accesstoken`, `invitation` tables (migration 0004), column for column with fastapi-users' base tables | R-050 | done |
| 2 | fastapi-users per application: manager, password rule, database sessions in a cookie, reset hook | R-051, R-604 | done |
| 3 | Invitations: issue (digest only), atomic claim, release on failure, status; the registration route | R-050, R-601, R-602 | done |
| 4 | Roles, the capability table, the invitation ceiling, the last admin | R-052 | done |
| 5 | The mail sender: STARTTLS, a CA bundle option; mailed or shown once | R-051 | done |
| 6 | Admin actions: role changes, reset links | R-051, R-052 | done |
| 7 | `POST /api/slide-cases` for contributors, override for curators | R-052 | done |
| 8 | Same-origin writes | R-603 | done |
| 9 | The first admin from the command line | R-050 | done |
| 10 | Account, invitation and created-case records in the contract and TypeScript; generated data-contract pages | (contracts) | done |
| 11 | Wiki page 07 with its diagram (both themes checked), the fastapi-users card, design, guide section; version 0.05.000 | (documentation and versioning standards) | done |

## Convergence verdict (2026-09-29, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-050 registration only by invitation | `tests/accounts/test_accounts.py::test_registration_requires_invitation` | pass (Windows and Ubuntu) |
| R-051 mail sender, or the link to the issuer only | `tests/accounts/test_accounts.py::test_mail_adapter_against_local_sink` (aiosmtpd sink requiring STARTTLS, a test certificate as CA) | pass (both) |
| R-052 roles enforced | `tests/accounts/test_roles.py::test_role_matrix` (the table for every role; every existing route for every role and a visitor) | pass (both) |
| R-601 one account per link under a race | `tests/accounts/test_accounts.py::test_one_link_one_account_under_a_race` (six concurrent registrations) | pass (both) |
| R-602 no open registration | `tests/accounts/test_accounts.py::test_no_open_registration_route` | pass (both) |
| R-603 cross-site writes refused | `tests/accounts/test_roles.py::test_cross_site_writes_are_refused` | pass (both) |
| R-604 sign-out ends the session | `tests/accounts/test_roles.py::test_sessions_end_at_sign_out` | pass (both) |

The full suite ran on the production host (Ubuntu 24.04) with the fixtures and deprecation warnings as errors, and on
the development machine (Windows), where only U3's three container gates are skipped; the counts are in the pull
request.

Unmet: none. Owed by later units: the tus hook's authorisation and per-account quota (U5), the join, sign-in, reset
and invitation pages (U12), identify and moderate routes on the same table (U13), the secret key from the vault, the
first admin on the server and login rate limiting in nginx (U16).
