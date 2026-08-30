import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../lib/api/client";
import { clubDetail } from "../test/fixtures";
import { ClubDetailPage, CreateClub, Discover } from "./Clubs";

function detailRoute() {
  return (
    <MemoryRouter initialEntries={["/clubs/club-1"]}>
      <Routes><Route path="/clubs/:clubId" element={<ClubDetailPage />} /></Routes>
    </MemoryRouter>
  );
}

describe("club flows", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders discovery results", async () => {
    vi.spyOn(api, "clubs").mockResolvedValue({ results: [clubDetail()] });
    render(<MemoryRouter><Discover /></MemoryRouter>);
    expect(await screen.findByText("Literary Society")).toBeInTheDocument();
    expect(screen.getByText("4 members")).toBeInTheDocument();
  });

  it("renders empty discovery", async () => {
    vi.spyOn(api, "clubs").mockResolvedValue({ results: [] });
    render(<MemoryRouter><Discover /></MemoryRouter>);
    expect(await screen.findByText("No societies found")).toBeInTheDocument();
  });

  it("creates a join request", async () => {
    vi.spyOn(api, "club").mockResolvedValue(clubDetail());
    const join = vi.spyOn(api, "join").mockResolvedValue({
      id: "request-1",
      status: "PENDING",
      rejection_reason: "",
      created_at: "2026-08-30T00:00:00Z",
      updated_at: "2026-08-30T00:00:00Z",
      student: { first_name: "Sam", last_name: "Student", group: "10-A", about: "", profile_photo_url: "", interests: [] },
    });
    render(detailRoute());
    fireEvent.click(await screen.findByRole("button", { name: "Request to join" }));
    await waitFor(() => expect(join).toHaveBeenCalledWith("club-1"));
  });

  it("cancels only the current request ID", async () => {
    vi.spyOn(api, "club").mockResolvedValue(clubDetail({
      request_status: "PENDING",
      request_id: "request-1",
    }));
    const cancel = vi.spyOn(api, "cancel").mockResolvedValue({
      id: "request-1",
      status: "CANCELLED",
      rejection_reason: "",
      created_at: "2026-08-30T00:00:00Z",
      updated_at: "2026-08-30T00:00:00Z",
      student: { first_name: "Sam", last_name: "Student", group: "10-A", about: "", profile_photo_url: "", interests: [] },
    });
    render(detailRoute());
    fireEvent.click(await screen.findByRole("button", { name: "Cancel request" }));
    await waitFor(() => expect(cancel).toHaveBeenCalledWith("request-1"));
  });

  it("leaves an active membership", async () => {
    vi.spyOn(api, "club").mockResolvedValue(clubDetail({ membership_status: "MEMBER" }));
    const leave = vi.spyOn(api, "leave").mockResolvedValue(undefined);
    render(detailRoute());
    fireEvent.click(await screen.findByRole("button", { name: "Leave society" }));
    await waitFor(() => expect(leave).toHaveBeenCalledWith("club-1"));
  });

  it("submits a security-minimal create-club payload", async () => {
    vi.spyOn(api, "interests").mockResolvedValue({ results: [] });
    const create = vi.spyOn(api, "createClub").mockResolvedValue(clubDetail({ status: "PENDING" }));
    render(<MemoryRouter><CreateClub /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "New Society" } });
    fireEvent.change(screen.getByLabelText("Short description"), { target: { value: "Short" } });
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Long" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit for review" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({
      name: "New Society",
      short_description: "Short",
      description: "Long",
      category: "OTHER",
      interest_ids: [],
    }));
    const payload = create.mock.calls[0][0] as unknown as Record<string, unknown>;
    expect(payload).not.toHaveProperty("owner");
    expect(payload).not.toHaveProperty("lyceum");
    expect(payload).not.toHaveProperty("status");
  });
});
