import { create } from "zustand";

export type AuthRole = "admin" | "agent";

export interface AuthSession {
  role: AuthRole;
  agentId: string | null;
  username: string;
}

interface AuthStore {
  session: AuthSession | null;
  setSession: (session: AuthSession | null) => void;
  clearSession: () => void;
  isAgentAccount: () => boolean;
  isAdminAccount: () => boolean;
  boundAgentId: () => string | null;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  session: null,

  setSession: (session) => set({ session }),

  clearSession: () => set({ session: null }),

  isAgentAccount: () => get().session?.role === "agent",

  isAdminAccount: () => get().session?.role !== "agent",

  boundAgentId: () => {
    const session = get().session;
    return session?.role === "agent" ? session.agentId : null;
  },
}));

export function applyAuthSession(
  payload: {
    role?: AuthRole;
    agent_id?: string | null;
    username?: string;
  } | null,
): void {
  if (!payload?.username) {
    useAuthStore.getState().clearSession();
    return;
  }

  const role = payload.role === "agent" ? "agent" : "admin";
  useAuthStore.getState().setSession({
    role,
    agentId: role === "agent" ? payload.agent_id ?? null : null,
    username: payload.username,
  });
}
