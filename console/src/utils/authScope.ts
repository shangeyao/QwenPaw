const ADMIN_ONLY_ROUTE_PREFIXES = [
  "/accounts",
  "/agents",
  "/models",
  "/environments",
  "/security",
  "/token-usage",
  "/agent-stats",
  "/voice-transcription",
  "/debug",
  "/backups",
  "/plugin-manager",
  "/skill-pool",
] as const;

export function isAdminOnlyRoute(pathname: string): boolean {
  return ADMIN_ONLY_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function belongsToBoundAgent(
  agentId: string | null | undefined,
  boundAgentId: string | null,
): boolean {
  if (!boundAgentId) {
    return true;
  }
  return (agentId || "default") === boundAgentId;
}
