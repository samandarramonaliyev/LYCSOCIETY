import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../lib/api/client";
import { TelegramGroupPanel } from "./TelegramGroupPanel";

describe("Telegram group UI", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows the not-linked owner state", async () => {
    vi.spyOn(api, "telegramStatus").mockResolvedValue({
      linked: false,
      title: "",
      status: "UNLINKED",
      linked_at: null,
    });
    render(<TelegramGroupPanel clubId="club-1" owner />);
    expect(await screen.findByText("No Telegram group is linked.")).toBeInTheDocument();
  });

  it("generates a short-lived link challenge", async () => {
    vi.spyOn(api, "telegramStatus").mockResolvedValue({ linked: false, title: "", status: "UNLINKED", linked_at: null });
    const start = vi.spyOn(api, "telegramStart").mockResolvedValue({ token: "challenge-token", expires_in: 600 });
    render(<TelegramGroupPanel clubId="club-1" owner />);
    fireEvent.click(await screen.findByRole("button", { name: "Generate link challenge" }));
    expect(await screen.findByText(/\/connect challenge-token/)).toBeInTheDocument();
    expect(start).toHaveBeenCalledWith("club-1");
  });

  it("renders and unlinks a linked group", async () => {
    vi.spyOn(api, "telegramStatus").mockResolvedValue({
      linked: true,
      title: "Private Readers",
      status: "LINKED",
      linked_at: "2026-08-30T00:00:00Z",
    });
    const unlink = vi.spyOn(api, "telegramUnlink").mockResolvedValue(undefined);
    render(<TelegramGroupPanel clubId="club-1" owner />);
    expect(await screen.findByText("Linked to Private Readers.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Unlink group" }));
    await waitFor(() => expect(unlink).toHaveBeenCalledWith("club-1"));
    expect(await screen.findByText("No Telegram group is linked.")).toBeInTheDocument();
  });

  it("returns a member invite without persisting it across mounts", async () => {
    const invite = vi.spyOn(api, "telegramInvite").mockResolvedValue({
      invite_link: "https://t.me/+temporary",
    });
    const first = render(<TelegramGroupPanel clubId="club-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Request Telegram invite" }));
    expect(await screen.findByRole("link", { name: "Open invite" })).toHaveAttribute(
      "href",
      "https://t.me/+temporary",
    );
    expect(invite).toHaveBeenCalledWith("club-1");
    first.unmount();
    render(<TelegramGroupPanel clubId="club-1" />);
    expect(screen.queryByRole("link", { name: "Open invite" })).not.toBeInTheDocument();
  });

  it("shows a safe failure state without an invite", async () => {
    vi.spyOn(api, "telegramInvite").mockRejectedValue(new Error("Telegram unavailable"));
    render(<TelegramGroupPanel clubId="club-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Request Telegram invite" }));
    expect(await screen.findByText("Telegram unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open invite" })).not.toBeInTheDocument();
  });
});
