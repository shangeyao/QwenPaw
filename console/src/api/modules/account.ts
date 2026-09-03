import { request } from "../request";
import type {
  CreateWebAccountRequest,
  UpdateWebAccountRequest,
  WebAccountListResponse,
  WebAccountSummary,
} from "../types/account";

export const accountApi = {
  listAccounts: () => request<WebAccountListResponse>("/auth/accounts"),

  createAccount: (payload: CreateWebAccountRequest) =>
    request<WebAccountSummary>("/auth/accounts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateAccount: (username: string, payload: UpdateWebAccountRequest) =>
    request<WebAccountSummary>(
      `/auth/accounts/${encodeURIComponent(username)}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    ),

  deleteAccount: (username: string) =>
    request<{ success: boolean; username: string }>(
      `/auth/accounts/${encodeURIComponent(username)}`,
      { method: "DELETE" },
    ),
};
