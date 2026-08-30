import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../lib/api/client";
import type { Meeting, NotificationPreference } from "../types/api";
import { ClubAnnouncements, ClubMeetings, Notifications, Settings } from "./Phase6D";

const meeting: Meeting = {
  id: "meeting-1",
  title: "Weekly meeting",
  description: "Agenda",
  starts_at: "2026-09-01T10:00:00Z",
  location: "Room 1",
  status: "SCHEDULED",
  created_at: "2026-08-30T00:00:00Z",
};

function meetingPage() {
  return (
    <MemoryRouter initialEntries={["/clubs/club-1/meetings"]}>
      <Routes><Route path="/clubs/:clubId/meetings" element={<ClubMeetings />} /></Routes>
    </MemoryRouter>
  );
}

describe("meeting, announcement, and notification flows", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("lists meetings and saves GOING and NOT_GOING RSVP states", async () => {
    vi.spyOn(api, "meetings").mockResolvedValue({ results: [meeting] });
    const rsvp = vi.spyOn(api, "rsvp")
      .mockResolvedValueOnce({ response: "GOING" })
      .mockResolvedValueOnce({ response: "NOT_GOING" });
    render(meetingPage());
    expect(await screen.findByText("Weekly meeting")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Going" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Going" })).toHaveAttribute("aria-pressed", "true"));
    fireEvent.click(screen.getByRole("button", { name: "Not going" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Not going" })).toHaveAttribute("aria-pressed", "true"));
    expect(rsvp).toHaveBeenNthCalledWith(1, "meeting-1", "GOING");
    expect(rsvp).toHaveBeenNthCalledWith(2, "meeting-1", "NOT_GOING");
  });

  it("rolls back optimistic RSVP after failure", async () => {
    vi.spyOn(api, "meetings").mockResolvedValue({ results: [meeting] });
    vi.spyOn(api, "rsvp").mockRejectedValue(new Error("RSVP rejected"));
    render(meetingPage());
    const going = await screen.findByRole("button", { name: "Going" });
    fireEvent.click(going);
    expect(await screen.findByText("RSVP rejected")).toBeInTheDocument();
    expect(going).toHaveAttribute("aria-pressed", "false");
  });

  it("renders cancelled meetings without RSVP controls", async () => {
    vi.spyOn(api, "meetings").mockResolvedValue({
      results: [{ ...meeting, status: "CANCELLED" }],
    });
    render(meetingPage());
    expect(await screen.findByText("CANCELLED")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Going" })).not.toBeInTheDocument();
  });

  it("lists announcements with reporting action", async () => {
    vi.spyOn(api, "announcements").mockResolvedValue({
      results: [{ id: "announcement-1", title: "News", message: "Message", created_at: "2026-08-30T00:00:00Z" }],
    });
    render(
      <MemoryRouter initialEntries={["/clubs/club-1/announcements"]}>
        <Routes><Route path="/clubs/:clubId/announcements" element={<ClubAnnouncements />} /></Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText("News")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Report announcement" })).toBeInTheDocument();
  });

  it("shows unread notifications and marks only the selected one read", async () => {
    const unread = { id: "notification-1", type: "MEETING", title: "Reminder", body: "Soon", is_read: false, created_at: "2026-08-30T00:00:00Z" };
    vi.spyOn(api, "notifications").mockResolvedValue([unread]);
    const read = vi.spyOn(api, "readNotification").mockResolvedValue({ ...unread, is_read: true });
    render(<Notifications />);
    fireEvent.click(await screen.findByText("Reminder"));
    await waitFor(() => expect(read).toHaveBeenCalledWith("notification-1"));
  });

  it("renders an empty notification state", async () => {
    vi.spyOn(api, "notifications").mockResolvedValue([]);
    render(<Notifications />);
    expect(await screen.findByText("No notifications yet.")).toBeInTheDocument();
  });

  it("updates notification preferences", async () => {
    const preferences: NotificationPreference = {
      club_announcements: true,
      meeting_notifications: true,
      meeting_reminders: true,
    };
    vi.spyOn(api, "preferences").mockResolvedValue(preferences);
    const update = vi.spyOn(api, "updatePreferences").mockResolvedValue({
      ...preferences,
      meeting_reminders: false,
    });
    render(<Settings />);
    const checkbox = await screen.findByRole("checkbox", { name: "meeting reminders" });
    fireEvent.click(checkbox);
    await waitFor(() => expect(update).toHaveBeenCalledWith({ meeting_reminders: false }));
    expect(checkbox).not.toBeChecked();
  });

  it("rolls back a failed preference update", async () => {
    const preferences: NotificationPreference = {
      club_announcements: true,
      meeting_notifications: true,
      meeting_reminders: true,
    };
    vi.spyOn(api, "preferences").mockResolvedValue(preferences);
    vi.spyOn(api, "updatePreferences").mockRejectedValue(new Error("Preference rejected"));
    render(<Settings />);
    const checkbox = await screen.findByRole("checkbox", { name: "meeting reminders" });
    fireEvent.click(checkbox);
    expect(await screen.findByText("Preference rejected")).toBeInTheDocument();
    expect(checkbox).toBeChecked();
  });
});
