# fastapi-users

## What and why

fastapi-users provides registration, sign-in, sessions, password reset and account routes for FastAPI, with pluggable
transports (cookie or bearer) and strategies (database tokens or JWT), and hashes passwords with pwdlib (Argon2,
bcrypt). ADR-0044 makes it the default for FastAPI apps with users: accounts in the app's own database, no
per-account bill, no vendor.

## Install (exact, verified)

`fastapi-users==15.0.5` and `fastapi-users-db-sqlalchemy==7.0.0` (in `requirements-api.txt`); they bring
`pwdlib[argon2,bcrypt]==0.3.0` and `PyJWT` 2.15.1.

## Usage

```python
from app.accounts.users import build

accounts = build(settings)                      # cookie transport, database strategy, the user manager
app.include_router(accounts.users.get_auth_router(accounts.backend), prefix="/api/auth")
current = accounts.users.current_user(active=True)
```

## Applying it here

`app/accounts/users.py` builds the objects per application; `app/routers/accounts.py` mounts sign-in and sign-out,
password reset and the account routes, and replaces registration with the invitation route. Roles are Laminario's
own (`app/accounts/roles.py`), checked on top of fastapi-users' "current active user".

## Caveats and licence

- The project is in maintenance mode (security fixes only, F-011); watched in ADR-0077.
- Its base tables are named `user` and `accesstoken`, with 36-character GUID ids on SQLite; migration 0004 writes
  them column for column and the migration gate compares them with the models.
- Its register route is not mounted: registration is only by invitation.
- With `from __future__ import annotations`, FastAPI cannot resolve dependency aliases defined inside a factory
  function; the accounts router module does not use it.
- MIT.
