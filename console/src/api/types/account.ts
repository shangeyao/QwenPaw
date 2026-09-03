export type WebAccountRole = "admin" | "agent";

export interface WebAccountSummary {
  username: string;
  role: WebAccountRole;
  agent_id?: string | null;
}

export interface WebAccountListResponse {
  accounts: WebAccountSummary[];
}

export interface CreateWebAccountRequest {
  username: string;
  password: string;
  role: WebAccountRole;
  agent_id?: string | null;
}

export interface UpdateWebAccountRequest {
  new_username?: string | null;
  password?: string | null;
  agent_id?: string | null;
  current_password?: string | null;
}
