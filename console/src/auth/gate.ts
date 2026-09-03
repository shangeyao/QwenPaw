import { authApi, type AuthStatusResponse } from "../api/modules/auth";
import { clearAuthToken, getApiToken, getApiUrl } from "../api/config";
import { applyAuthSession } from "../stores/authStore";
import { useAgentStore } from "../stores/agentStore";

export type AuthGateState = "ok" | "auth-required";
export type BackendMode = "standard" | "hub";

export interface BackendInfo {
  mode: BackendMode;
  authStatus: AuthStatusResponse;
}

export async function resolveBackendInfo(): Promise<BackendInfo> {
  const authStatus = await authApi.getStatus();
  return {
    mode: authStatus.mode === "hub" ? "hub" : "standard",
    authStatus,
  };
}

export async function resolveBackendMode(): Promise<BackendMode> {
  return (await resolveBackendInfo()).mode;
}

export async function resolveAuthGate(
  knownStatus?: AuthStatusResponse,
): Promise<AuthGateState> {
  const status = knownStatus ?? (await authApi.getStatus());
  if (!status.enabled) {
    applyAuthSession(null);
    return "ok";
  }

  const token = getApiToken();
  if (!token) {
    applyAuthSession(null);
    return "auth-required";
  }

  const response = await fetch(getApiUrl("/auth/verify"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.ok) {
    const verified = (await response.json()) as {
      username?: string;
      role?: "admin" | "agent";
      agent_id?: string | null;
    };
    applyAuthSession(verified);
    if (verified.role === "agent" && verified.agent_id) {
      useAgentStore.getState().setSelectedAgent(verified.agent_id);
    }
    return "ok";
  }
  if (response.status === 401 || response.status === 403) {
    clearAuthToken();
    applyAuthSession(null);
    return "auth-required";
  }
  throw new Error(`Authentication service returned ${response.status}`);
}
