import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AuthState } from "../types/api";
import { currentUser } from "../test/fixtures";

const { bootstrapAuth } = vi.hoisted(() => ({ bootstrapAuth: vi.fn() }));
vi.mock("../lib/auth", () => ({
  bootstrapAuth,
  authStateForUser: (user: { account_status: string; verification_status: string }) =>
    user.account_status === "SUSPENDED"
      ? "SUSPENDED"
      : user.verification_status === "VERIFIED" ? "VERIFIED" : "UNVERIFIED",
}));

import { AuthProvider, useAuth } from "./AuthProvider";

function Probe() {
  const { state } = useAuth();
  return <div>{state}</div>;
}

describe("AuthProvider states", () => {
  it("shows authenticating while bootstrap is pending and then verified", async () => {
    let resolve!: (value: { state: AuthState; user: ReturnType<typeof currentUser> }) => void;
    bootstrapAuth.mockReturnValueOnce(new Promise((next) => { resolve = next; }));
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(screen.getByText("AUTHENTICATING")).toBeInTheDocument();
    resolve({ state: "VERIFIED", user: currentUser() });
    expect(await screen.findByText("VERIFIED")).toBeInTheDocument();
  });

  it.each(["UNVERIFIED", "SUSPENDED", "ERROR"] as AuthState[])(
    "renders the %s bootstrap state",
    async (state) => {
      bootstrapAuth.mockResolvedValueOnce({ state });
      render(<AuthProvider><Probe /></AuthProvider>);
      expect(await screen.findByText(state)).toBeInTheDocument();
    },
  );
});
