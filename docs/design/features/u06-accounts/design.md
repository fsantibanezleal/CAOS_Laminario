# U6 · Accounts and roles · design

The flows, with their diagram, are in the wiki page [07 Accounts and roles](../../../architecture/07_accounts.md);
this page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| `user`, `accesstoken`, `invitation` tables | migration 0004, `app/db/models.py` |
| fastapi-users wired per application: manager, cookie sessions, password rule, reset hook | `app/accounts/users.py` |
| Invitations: issue, atomic claim, release, status | `app/accounts/invitations.py` |
| Roles and the capability table | `app/accounts/roles.py` |
| The optional mail sender | `app/accounts/mail.py` |
| Routes: sign-in, registration, reset, the account itself, invitations, admin actions, creating a slide case | `app/routers/accounts.py` |
| Same-origin writes | the middleware in `app/main.py` |
| The first admin | `python -m app.accounts invite --role admin` |
| Account, invitation and created-case records | the catalog contract and its TypeScript types |

## Decisions

- **fastapi-users 15.0.5 (ADR-0044)**, with fastapi-users-db-sqlalchemy 7.0.0: accounts and sessions live in the
  app's own SQLite database. The project is in maintenance mode (security fixes only, F-011); it is the recorded
  default and what the ml box already runs for QMine.
- **Database sessions in a cookie.** An opaque token in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` in
  production) whose row sign-out deletes, rather than a stateless JWT that stays valid until it expires (R-604).
- **No open registration.** The fastapi-users register route is not mounted; the only registration route needs an
  invitation token (R-602). Invitations are 32 random bytes in a link, stored only as their SHA-256, valid seven
  days, usable once. The claim is one conditional `UPDATE`; six simultaneous registrations with one link create one
  account (R-601). A failed registration (email taken, weak password, wrong address) releases the claim.
- **Roles are ranks** (contributor < identifier < curator < admin), and one table maps each capability to the
  lowest role that has it; every route checks through it and the role-matrix gate walks it (R-052). Curators
  invite up to identifier; admins invite anyone and change roles; the last admin cannot lose the role.
  `is_superuser` mirrors the admin role for fastapi-users' own admin routes. An account cannot change its role.
- **The command line is the trust root.** The first admin comes from `python -m app.accounts invite --role admin`
  on the server; whoever can run it could change the database anyway.
- **Mail is optional (BL-023).** With `LAMINARIO_SMTP_HOST` and `LAMINARIO_SMTP_SENDER` set, invitations with an
  address and reset links are mailed over SMTP with STARTTLS (port 587 is what the ml box reaches, F-013). Without
  it, an invitation's link is in the answer that created it, to that issuer only, and never again (the token is not
  stored); an admin issues a reset link for a person who asks (R-051).
- **Passwords**: at least 12 characters, not containing the email's local part; hashed by fastapi-users (pwdlib,
  Argon2). Reset tokens are signed with `LAMINARIO_SECRET_KEY` (required in production, from the vault) and last
  one hour.
- **Same-origin writes.** A browser always sends `Origin` on cross-site requests; state-changing requests with a
  foreign `Origin` are refused, reads stay open (R-603). With `SameSite=Lax` cookies, this closes cross-site request
  forgery without tokens in forms.
- **Contributors create slide cases.** `POST /api/slide-cases` stores a validated case as the contributor's draft;
  a placement override needs a curator, and base-collection cases come only from the import.

## Interfaces used by later units

- U5 (uploads): the tus hook authorises by the session and counts quota per account.
- U12 (contribute): the pages for joining, signing in, resetting and inviting.
- U13 (identify, moderation): routes checked through the same capability table (`identify`, `moderate`).
- U16 (deploy): `LAMINARIO_SECRET_KEY` from the vault; the first admin invited from the server's command line;
  login rate limiting in nginx.
