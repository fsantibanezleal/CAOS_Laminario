// The two rooms. The room follows the system's light or dark preference until the visitor chooses one; the choice
// is kept on this device. The inline script in index.html sets data-theme before the first paint, so the page never
// shows the other room first; this module takes over from there and follows system changes while no choice is made.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Room = "daylight" | "lamplit";
export type RoomChoice = Room | "system";
const STORAGE_KEY = "laminario.theme";
const DARK = "(prefers-color-scheme: dark)";

function stored(): RoomChoice {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "daylight" || value === "lamplit" ? value : "system";
  } catch {
    return "system";
  }
}

const systemRoom = (): Room => (window.matchMedia?.(DARK).matches ? "lamplit" : "daylight");

interface RoomState {
  choice: RoomChoice;
  room: Room;
  setChoice: (choice: RoomChoice) => void;
}

const Context = createContext<RoomState | null>(null);

export function RoomProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<RoomChoice>(stored);
  const [system, setSystem] = useState<Room>(systemRoom);

  useEffect(() => {
    const query = window.matchMedia?.(DARK);
    if (!query) return undefined;
    const follow = () => setSystem(query.matches ? "lamplit" : "daylight");
    query.addEventListener("change", follow);
    return () => query.removeEventListener("change", follow);
  }, []);

  const room: Room = choice === "system" ? system : choice;

  useEffect(() => {
    document.documentElement.dataset.theme = room;
  }, [room]);

  const setChoice = useCallback((next: RoomChoice) => {
    try {
      if (next === "system") localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // storage may be blocked; the choice then lasts for this page only
    }
    setChoiceState(next);
  }, []);

  const value = useMemo(() => ({ choice, room, setChoice }), [choice, room, setChoice]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useRoom(): RoomState {
  const value = useContext(Context);
  if (!value) throw new Error("useRoom outside RoomProvider");
  return value;
}
