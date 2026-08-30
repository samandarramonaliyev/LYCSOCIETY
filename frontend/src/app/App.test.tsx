import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { AuthState } from "../types/api";

const auth = vi.hoisted(() => ({ state: "VERIFIED" as AuthState }));
vi.mock("./AuthProvider", () => ({
  useAuth: () => auth,
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

import { RequireVerified } from "./App";

function renderProtected(state: AuthState) {
  auth.state = state;
  render(
    <MemoryRouter initialEntries={["/private"]}>
      <Routes>
        <Route path="/" element={<div>Onboarding home</div>} />
        <Route
          path="/private"
          element={<RequireVerified><div>Protected content</div></RequireVerified>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("protected route behavior", () => {
  it("renders protected content for verified users", () => {
    renderProtected("VERIFIED");
    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });

  it("redirects unverified users to onboarding", async () => {
    renderProtected("UNVERIFIED");
    expect(await screen.findByText("Onboarding home")).toBeInTheDocument();
  });

  it.each([
    ["AUTHENTICATING", "Authenticating"],
    ["SUSPENDED", "This account is suspended"],
    ["TELEGRAM_UNAVAILABLE", "Open LYC Society inside Telegram"],
    ["ERROR", "Authentication could not be completed"],
  ] as const)("renders %s safely", (state, message) => {
    renderProtected(state);
    expect(screen.getByText(message)).toBeInTheDocument();
  });
});
