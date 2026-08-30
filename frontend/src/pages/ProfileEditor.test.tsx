import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InterestSelector } from "../components/InterestSelector";
import { api } from "../lib/api/client";
import { profile } from "../test/fixtures";
import { ProfileEditor } from "./ProfileEditor";

describe("profile editing", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "profile").mockResolvedValue({ ...profile });
    vi.spyOn(api, "interests").mockResolvedValue({ results: [] });
  });

  it("renders verified identity as immutable text and editable profile fields", async () => {
    render(<ProfileEditor />);
    expect(await screen.findByText("Test Lyceum · 10-A")).toBeInTheDocument();
    expect(screen.getByDisplayValue("About Sam")).toBeEnabled();
    expect(screen.getByDisplayValue("Chess")).toBeEnabled();
    expect(screen.queryByDisplayValue("Test Lyceum")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("10-A")).not.toBeInTheDocument();
  });

  it("saves only about and hobbies", async () => {
    const update = vi.spyOn(api, "updateProfile").mockResolvedValue({
      ...profile,
      about: "Updated about",
      hobbies: "Reading",
    });
    render(<ProfileEditor />);
    fireEvent.change(await screen.findByDisplayValue("About Sam"), {
      target: { value: "Updated about" },
    });
    fireEvent.change(screen.getByDisplayValue("Chess"), { target: { value: "Reading" } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith({
      about: "Updated about",
      hobbies: "Reading",
    }));
    expect(await screen.findByText("Profile saved.")).toBeInTheDocument();
  });

  it("shows failed save without claiming success", async () => {
    vi.spyOn(api, "updateProfile").mockRejectedValue(new Error("Save rejected"));
    render(<ProfileEditor />);
    fireEvent.click(await screen.findByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("Save rejected")).toBeInTheDocument();
    expect(screen.queryByText("Profile saved.")).not.toBeInTheDocument();
  });

  it("enforces at most ten interests before sending the payload", async () => {
    const interests = Array.from({ length: 11 }, (_, index) => ({
      id: `interest-${index}`,
      name: `Interest ${index}`,
      slug: `interest-${index}`,
    }));
    vi.spyOn(api, "interests").mockResolvedValue({ results: interests });
    const update = vi.spyOn(api, "updateProfile").mockResolvedValue({ ...profile });
    render(<InterestSelector selected={interests.slice(0, 10)} />);
    expect(await screen.findByText("10 / 10 selected")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Interest 10" }));
    expect(screen.getByText("10 / 10 selected")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save interests" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith({
      interest_ids: interests.slice(0, 10).map((interest) => interest.id),
    }));
  });
});
