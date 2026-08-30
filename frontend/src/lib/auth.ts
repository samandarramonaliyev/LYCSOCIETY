import { api, ApiClientError } from "./api/client";
import { initializeTelegram } from "./telegram";
import type { AuthState, CurrentUser } from "../types/api";

export function authStateForUser(user: CurrentUser): AuthState {
  if (user.account_status === "SUSPENDED" || user.verification_status === "SUSPENDED") {
    return "SUSPENDED";
  }
  return user.verification_status === "VERIFIED" ? "VERIFIED" : "UNVERIFIED";
}

export async function bootstrapAuth(): Promise<{ state: AuthState; user?: CurrentUser }> {
  const app = initializeTelegram();
  if (!app) return { state: "TELEGRAM_UNAVAILABLE" };

  try {
    const existingUser = await api.me();
    return { state: authStateForUser(existingUser), user: existingUser };
  } catch (error) {
    if (!(error instanceof ApiClientError) || ![401, 403].includes(error.status ?? 0)) {
      return { state: "ERROR" };
    }
  }

  try {
    await api.csrf();
    const authenticated = await api.authenticate(app.initData);
    return {
      state: authStateForUser(authenticated.user),
      user: authenticated.user,
    };
  } catch {
    return { state: "ERROR" };
  }
}
