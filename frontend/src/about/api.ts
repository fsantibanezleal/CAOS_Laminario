// GET /api/about (U15): the collection counted when it is read, and the credits.
import { send } from "../api/client";
import type { AboutRecord } from "../contract/catalog";

export const aboutApi = {
  read: (signal?: AbortSignal) => send<AboutRecord>("GET", "/api/about", undefined, signal) as Promise<AboutRecord>,
};
