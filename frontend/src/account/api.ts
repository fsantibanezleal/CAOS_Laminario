// The account API (U6): sign in and out with a session cookie, register from an invitation link, ask for and complete
// a password reset. fastapi-users answers a refusal with a code ("LOGIN_BAD_CREDENTIALS", or {code, reason}); the
// places word each code in the page's language, and fall back to the server's reason for one they do not know.
import type { AccountRecord } from "../contract/catalog";
import { send } from "../api/client";

/** The password rules of app/accounts/users.py, checked here first so their words are the page's own. */
export const MIN_PASSWORD_LENGTH = 12;

export type PasswordProblem = "password.short" | "password.email" | "password.mismatch";

export function passwordProblem(password: string, email: string, repeated?: string): PasswordProblem | null {
  if (password.length < MIN_PASSWORD_LENGTH) return "password.short";
  const local = email.split("@", 1)[0].toLowerCase();
  if (local.length >= 4 && password.toLowerCase().includes(local)) return "password.email";
  if (repeated !== undefined && repeated !== password) return "password.mismatch";
  return null;
}

export const accountApi = {
  /** fastapi-users' login takes a form, with the email as the username; 204 and the cookie on success. */
  signIn: (email: string, password: string) =>
    send<null>("POST", "/api/auth/login", new URLSearchParams({ username: email, password })),
  signOut: () => send<null>("POST", "/api/auth/logout"),
  register: (token: string, email: string, password: string, displayName: string) =>
    send<AccountRecord>("POST", "/api/auth/register", { token, email, password, display_name: displayName }),
  /** Always 202, whether or not the address has an account (so the answer tells nobody which addresses do). */
  forgot: (email: string) => send<null>("POST", "/api/auth/forgot-password", { email }),
  reset: (token: string, password: string) => send<null>("POST", "/api/auth/reset-password", { token, password }),
};

/** The i18n key of an account refusal's code; null for a code the interface has no words for. */
export function refusalKey(code: string | null): string | null {
  switch (code) {
    case "LOGIN_BAD_CREDENTIALS":
      return "account.error.credentials";
    case "LOGIN_USER_NOT_VERIFIED":
      return "account.error.unverified";
    case "REGISTER_INVITATION_INVALID":
      return "account.error.invitation";
    case "REGISTER_INVITATION_OTHER_EMAIL":
      return "account.error.invitationEmail";
    case "REGISTER_USER_ALREADY_EXISTS":
      return "account.error.exists";
    case "RESET_PASSWORD_BAD_TOKEN":
      return "account.error.resetToken";
    default:
      return null;
  }
}

/** Where a place that needs an account sends a visitor: sign in, then back to where they were going. */
export function signInHref(next: string): string {
  return `/signin?next=${encodeURIComponent(next)}`;
}

/** A safe place to go after signing in: a path of this site, never another origin. */
export function safeNext(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/contribute";
  return value;
}
