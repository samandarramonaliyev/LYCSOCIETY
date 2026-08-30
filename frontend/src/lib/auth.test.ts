import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiClientError } from "./api/client";
import { authStateForUser, bootstrapAuth } from "./auth";
import { currentUser } from "../test/fixtures";

describe("Telegram authentication bootstrap", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    delete window.Telegram;
  });

  function installTelegram() {
    const webApp = { initData: "signed-init-data", ready: vi.fn(), expand: vi.fn() };
    window.Telegram = { WebApp: webApp };
    return webApp;
  }

  it("reports Telegram unavailable without making API requests", async () => {
    const me = vi.spyOn(api, "me");
    await expect(bootstrapAuth()).resolves.toEqual({ state: "TELEGRAM_UNAVAILABLE" });
    expect(me).not.toHaveBeenCalled();
  });

  it("uses an existing verified session before replaying initData", async () => {
    const app = installTelegram();
    const user = currentUser();
    vi.spyOn(api, "me").mockResolvedValue(user);
    const authenticate = vi.spyOn(api, "authenticate");

    await expect(bootstrapAuth()).resolves.toEqual({ state: "VERIFIED", user });
    expect(app.ready).toHaveBeenCalled();
    expect(app.expand).toHaveBeenCalled();
    expect(authenticate).not.toHaveBeenCalled();
  });

  it("authenticates and returns an unverified user when no session exists", async () => {
    installTelegram();
    const user = currentUser({
      verification_status: "UNVERIFIED",
      can_access_student_features: false,
      verified_student: null,
    });
    vi.spyOn(api, "me").mockRejectedValue(new ApiClientError({ message: "No session", status: 403 }));
    vi.spyOn(api, "csrf").mockResolvedValue({ csrf_token: "csrf" });
    vi.spyOn(api, "authenticate").mockResolvedValue({
      authenticated: true,
      csrf_token: "csrf-2",
      user,
    });

    await expect(bootstrapAuth()).resolves.toEqual({ state: "UNVERIFIED", user });
    expect(api.authenticate).toHaveBeenCalledWith("signed-init-data");
  });

  it("returns a safe error state for authentication failure", async () => {
    installTelegram();
    vi.spyOn(api, "me").mockRejectedValue(new ApiClientError({ message: "No session", status: 403 }));
    vi.spyOn(api, "csrf").mockRejectedValue(new Error("network"));
    await expect(bootstrapAuth()).resolves.toEqual({ state: "ERROR" });
  });

  it("maps suspended accounts before verified state", () => {
    const user = currentUser({ account_status: "SUSPENDED", verification_status: "SUSPENDED" });
    expect(authStateForUser(user)).toBe("SUSPENDED");
  });
});
