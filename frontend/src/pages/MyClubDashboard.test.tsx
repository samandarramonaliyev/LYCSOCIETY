import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../lib/api/client";
import { clubDetail } from "../test/fixtures";
import type { Meeting } from "../types/api";
import { MyClubDashboard } from "./MyClubDashboard";

const meeting: Meeting = {
  id: "meeting-1",
  title: "Existing meeting",
  description: "",
  starts_at: "2026-09-01T10:00:00Z",
  location: "Room",
  status: "SCHEDULED",
  created_at: "2026-08-30T00:00:00Z",
};

function mockActiveDashboard() {
  vi.spyOn(api, "mine").mockResolvedValue(clubDetail({ status: "ACTIVE" }));
  vi.spyOn(api, "requests").mockResolvedValue({ results: [] });
  vi.spyOn(api, "members").mockResolvedValue({ results: [] });
  vi.spyOn(api, "meetings").mockResolvedValue({ results: [meeting] });
  vi.spyOn(api, "announcements").mockResolvedValue({ results: [] });
  vi.spyOn(api, "telegramStatus").mockResolvedValue({ linked: false, title: "", status: "UNLINKED", linked_at: null });
}

describe("owner dashboard", () => {
  beforeEach(() => vi.restoreAllMocks());

  it.each([
    ["PENDING", undefined],
    ["REJECTED", "Needs more detail"],
  ] as const)("renders the %s club state", async (status, rejectionReason) => {
    vi.spyOn(api, "mine").mockResolvedValue(clubDetail({
      status,
      rejection_reason: rejectionReason,
    }));
    render(<MemoryRouter><MyClubDashboard /></MemoryRouter>);
    expect(await screen.findByText(status)).toBeInTheDocument();
    if (rejectionReason) expect(screen.getByText(rejectionReason)).toBeInTheDocument();
  });

  it("shows member roles and lets the owner accept or reject requests", async () => {
    mockActiveDashboard();
    vi.mocked(api.requests).mockResolvedValue({
      results: [
        { id: "request-1", status: "PENDING", rejection_reason: "", created_at: "", updated_at: "", student: { first_name: "Ada", last_name: "One", group: "10-A", about: "", profile_photo_url: "", interests: [] } },
        { id: "request-2", status: "PENDING", rejection_reason: "", created_at: "", updated_at: "", student: { first_name: "Lin", last_name: "Two", group: "10-B", about: "", profile_photo_url: "", interests: [] } },
      ],
    });
    vi.mocked(api.members).mockResolvedValue({
      results: [{ id: "member-1", role: "OWNER", joined_at: "", student: { first_name: "Owner", last_name: "Student", group: "10-A", profile_photo_url: "", interests: [] } }],
    });
    const decide = vi.spyOn(api, "decide").mockResolvedValue({ id: "member-2", role: "MEMBER", joined_at: "", student: { first_name: "Ada", last_name: "One", group: "10-A", profile_photo_url: "", interests: [] } });
    render(<MemoryRouter><MyClubDashboard /></MemoryRouter>);
    expect(await screen.findByText("OWNER")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Accept" })[0]);
    await waitFor(() => expect(decide).toHaveBeenCalledWith("request-1", "accept"));
    fireEvent.click(screen.getAllByRole("button", { name: "Reject" })[0]);
    await waitFor(() => expect(decide).toHaveBeenCalledWith("request-2", "reject"));
  });

  it("creates and cancels meetings with server-authorized payloads", async () => {
    mockActiveDashboard();
    const create = vi.spyOn(api, "createMeeting").mockResolvedValue({ ...meeting, id: "meeting-2", title: "New meeting" });
    const cancel = vi.spyOn(api, "cancelMeeting").mockResolvedValue({ ...meeting, status: "CANCELLED" });
    const { container } = render(<MemoryRouter><MyClubDashboard /></MemoryRouter>);
    expect(await screen.findByText("Existing meeting")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel meeting" }));
    await waitFor(() => expect(cancel).toHaveBeenCalledWith("meeting-1"));

    fireEvent.change(screen.getByPlaceholderText("Title"), { target: { value: "New meeting" } });
    const dateInput = container.querySelector('input[type="datetime-local"]') as HTMLInputElement;
    fireEvent.change(dateInput, { target: { value: "2026-09-02T12:00" } });
    fireEvent.change(screen.getByPlaceholderText("Location"), { target: { value: "Library" } });
    fireEvent.click(screen.getByRole("button", { name: "Create meeting" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith("club-1", expect.objectContaining({
      title: "New meeting",
      description: "",
      location: "Library",
    })));
    const payload = create.mock.calls[0][1] as unknown as Record<string, unknown>;
    expect(payload).not.toHaveProperty("created_by");
    expect(payload).not.toHaveProperty("club");
    expect(payload).not.toHaveProperty("status");
  });

  it("shows announcement creation failures without adding temporary content", async () => {
    mockActiveDashboard();
    vi.spyOn(api, "createAnnouncement").mockRejectedValue(new Error("Publish rejected"));
    render(<MemoryRouter><MyClubDashboard /></MemoryRouter>);
    fireEvent.change(await screen.findByPlaceholderText("Announcement title"), { target: { value: "News" } });
    fireEvent.change(screen.getByPlaceholderText("Message"), { target: { value: "Body" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish announcement" }));
    expect(await screen.findByText("Publish rejected")).toBeInTheDocument();
    expect(screen.queryByText("News")).not.toBeInTheDocument();
  });
});
