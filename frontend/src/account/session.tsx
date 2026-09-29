// Who is signed in, for every place: read once from GET /api/session (null for a visitor), read again after signing
// in or out. The roles' capabilities mirror app/accounts/roles.py, so a place offers only what the server allows
// (the server still checks every request).
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { AccountRecord } from "../contract/catalog";
import { accountApi } from "./api";

type Role = AccountRecord["role"];
const RANK: Record<Role, number> = { contributor: 1, identifier: 2, curator: 3, admin: 4 };

/** capability -> the lowest role that has it (app/accounts/roles.py, CAPABILITIES). */
const CAPABILITIES = {
  submit: "contributor",
  annotate: "contributor",
  identify: "identifier",
  moderate: "curator",
  override_placement: "curator",
  invite: "curator",
} as const satisfies Record<string, Role>;
export type Capability = keyof typeof CAPABILITIES;

export function allowed(account: AccountRecord | null | undefined, capability: Capability): boolean {
  return Boolean(account && account.is_active && RANK[account.role] >= RANK[CAPABILITIES[capability]]);
}

export interface Session {
  state: "loading" | "ready" | "error";
  account: AccountRecord | null;
  refresh: () => Promise<AccountRecord | null>;
  signOut: () => Promise<void>;
  can: (capability: Capability) => boolean;
}

const Context = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<Session["state"]>("loading");
  const [account, setAccount] = useState<AccountRecord | null>(null);

  const refresh = useCallback(async () => {
    try {
      const me = await api.me();
      setAccount(me);
      setState("ready");
      return me;
    } catch {
      setState("error");
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    try {
      await accountApi.signOut();
    } finally {
      await refresh();
    }
  }, [refresh]);

  const value = useMemo<Session>(() => ({
    state, account, refresh, signOut, can: (capability) => allowed(account, capability),
  }), [state, account, refresh, signOut]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useSession(): Session {
  const session = useContext(Context);
  if (!session) throw new Error("useSession outside SessionProvider");
  return session;
}
