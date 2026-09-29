# 07 · Accounts and roles

![Accounts and roles: invitations from the command line or from curators and admins, the atomic registration, sessions in a cookie, the capability table](svg/accounts.svg)

Everyone can look at every published slide without an account. Accounts exist for the people who add to the
collection, and there is no open sign-up: a curator or an admin invites each one (design document, non-goal 9).

## 1. Invitations

An invitation is a link carrying 32 random bytes (`/join?token=...`), valid for seven days and usable once. The
database keeps only the token's SHA-256, so a copy of the database cannot be used to register. An invitation
carries the role the new account will have and, optionally, the one email address that may use it.

| Who | May invite |
|---|---|
| the server's command line (`python -m app.accounts invite --role admin`) | anyone: this is how the first admin exists |
| a curator | contributors and identifiers |
| an admin | any role |

A curator sees and revokes the invitations it issued; an admin sees and revokes all of them. Each shows its status:
pending, used, expired or revoked.

**Mail is optional.** When a sender is configured (`LAMINARIO_SMTP_HOST` and `LAMINARIO_SMTP_SENDER`, credentials
from the vault), an invitation that names an address is mailed, over SMTP with STARTTLS on port 587, the port the
production host can reach (finding F-013). Otherwise the link appears in the answer that created it, to the person
who issued it, once: the token is not stored, so it cannot be shown again.

## 2. Registration

`POST /api/auth/register` takes the token, the email, a password and a display name:

1. **The claim.** One `UPDATE invitation SET used_at = now WHERE token_sha256 = ? AND used_at IS NULL AND revoked_at IS
   NULL AND expires_at > now`: SQLite runs it atomically, so six registrations racing with one link create one
   account (R-601).
2. **The address**, if the invitation names one, must match (case ignored).
3. **The account** is created with the invitation's role. The password needs at least 12 characters and must not
   contain the email's local part; fastapi-users hashes it with Argon2.

Any failure (an address that already has an account, a weak password, the wrong address) releases the claim, so the
link still works for a correct attempt. There is no other registration route: fastapi-users' own is not mounted
(R-602).

## 3. Sessions

Signing in (`POST /api/auth/login`) creates a row in `accesstoken` and sets a cookie holding its opaque token:
`HttpOnly`, `SameSite=Lax`, `Secure` in production, valid 30 days. Signing out deletes the row, so the cookie stops
working at once (R-604), which a stateless token could not do.

**Cross-site writes.** A browser always sends `Origin` on cross-site requests. Any `POST`, `PUT`, `PATCH` or
`DELETE` whose `Origin` is not this site is refused (403); reads stay open to any origin, as IIIF viewers need
(R-603). With `SameSite=Lax` cookies this closes cross-site request forgery without tokens in forms.

**Password reset.** fastapi-users signs a one-hour token with `LAMINARIO_SECRET_KEY`. With mail configured,
`POST /api/auth/forgot-password` mails the link; without it, an admin asks for a link for the person
(`POST /api/admin/accounts/{id}/reset-link`) and hands it over.

## 4. Roles

Each account has one role; each role includes everything the roles below it may do. One table maps each capability
to the lowest role that has it, and every route checks through it:

| Capability | Lowest role | Where |
|---|---|---|
| read | visitor (no account) | every public route |
| submit | contributor | `POST /api/slide-cases` |
| identify | identifier | identifications (U13) |
| moderate | curator | hiding, restoring, verifying (U13) |
| override placement | curator | a slide case with an override reason |
| invite | curator | `POST /api/invitations` (up to identifier) |
| manage invitations | admin | all invitations, any role |
| manage accounts | admin | roles, reset links |

An account cannot change its own role (`PATCH /api/users/me` ignores it), and the last admin cannot lose the role.
The role-matrix gate (R-052) walks the table for every role and calls every route that exists with every role and
without an account.

## 5. Contributing a slide case

`POST /api/slide-cases` runs the ingestion contract and stores the case as a draft of the signed-in contributor,
with the contract's flags in the answer. A placement override needs a curator; base-collection cases come only
from the import. The images arrive through uploads (U5) and are processed by the worker (U4).

## 6. How it is verified

| Gate | Checks |
|---|---|
| `tests/accounts/test_accounts.py` | no token, an unknown token, used, revoked, expired, the wrong address (released), a weak password, only digests stored; six racing registrations; no open route; the mail sender against a local SMTP sink that requires STARTTLS, and without a sender the link shown once and the admin's reset link |
| `tests/accounts/test_roles.py` | the capability table for every role; every route for every role and for a visitor; curators see their own invitations; an account cannot raise its role; the last admin; cross-site writes; sign-out |

## References

- fastapi-users 15.0.5. [fastapi-users.github.io/fastapi-users](https://fastapi-users.github.io/fastapi-users/).
- OWASP Cross-Site Request Forgery Prevention Cheat Sheet (verifying origin with standard headers; SameSite
  cookies). [cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
- RFC 3207, SMTP Service Extension for Secure SMTP over TLS (STARTTLS).
  [rfc-editor.org/rfc/rfc3207](https://www.rfc-editor.org/rfc/rfc3207).
