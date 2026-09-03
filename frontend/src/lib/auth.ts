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

  try {
    const existingUser = await api.me();
    return { state: authStateForUser(existingUser), user: existingUser };
  } catch (error) {
    if (!(error instanceof ApiClientError) || ![401, 403].includes(error.status ?? 0)) {
      return { state: "ERROR" };
    }
  }

  const initData = app?.initData.trim();
  if (initData) {
    try {
      await api.csrf();
      const authenticated = await api.authenticate(initData);
      return {
        state: authStateForUser(authenticated.user),
        user: authenticated.user,
      };
    } catch {
      return { state: "ERROR" };
    }
  }

  let localLoginSucceeded = false;
  try {
    await api.csrf();
    await api.devLogin();
    localLoginSucceeded = true;
    const user = await api.me();
    return {
      state: authStateForUser(user),
      user,
    };
  } catch (error) {
    if (
      !localLoginSucceeded
      && error instanceof ApiClientError
      && [403, 404].includes(error.status ?? 0)
    ) {
      return { state: "TELEGRAM_UNAVAILABLE" };
    }
    return { state: "ERROR" };
  }
}
