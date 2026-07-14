import { create } from "zustand";
import type { VaultSession } from "../lib/api-schemas";

/*
 * Session lives in memory ONLY — never localStorage. A page refresh drops
 * the token and requires re-unlocking with the key file. That is by design
 * (constitution Article I: identity IS the key file).
 */

type SessionState = {
  token: string | null;
  user_id: string | null;
  expires_at: string | null;
  unlock: (session: VaultSession) => void;
  lock: () => void;
};

export const use_session_store = create<SessionState>()((set) => ({
  token: null,
  user_id: null,
  expires_at: null,
  unlock: (session) =>
    set({
      token: session.token,
      user_id: session.user_id,
      expires_at: session.expires_at,
    }),
  lock: () => set({ token: null, user_id: null, expires_at: null }),
}));
