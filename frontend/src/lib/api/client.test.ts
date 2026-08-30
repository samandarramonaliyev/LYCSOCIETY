import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiClientError, request } from "./client";

describe("central API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    document.cookie = "csrftoken=secure%20csrf; path=/";
  });

  it("sends credentials and CSRF on unsafe JSON requests", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await request("/example/", { method: "PATCH", body: JSON.stringify({ value: 1 }) });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(init.credentials).toBe("include");
    expect(headers.get("X-CSRFToken")).toBe("secure csrf");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("does not attach CSRF to safe GET requests", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    await request("/example/");
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.has("X-CSRFToken")).toBe(false);
  });

  it("serializes the club creation allowlist without authority fields", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "club-1" }), { status: 201 }),
    );
    const payload = {
      name: "Society",
      short_description: "Short",
      description: "Long",
      category: "OTHER",
      interest_ids: ["interest-1"],
    };

    await api.createClub(payload);

    const body = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(body).toEqual(payload);
    expect(body).not.toHaveProperty("owner");
    expect(body).not.toHaveProperty("lyceum");
    expect(body).not.toHaveProperty("status");
    expect(body).not.toHaveProperty("role");
  });

  it("normalizes structured 401 and 403 responses", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: "NO_SESSION", message: "Sign in.", fields: {} } }), { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 403 }));

    await expect(request("/private/")).rejects.toMatchObject({
      name: "ApiClientError",
      status: 401,
      code: "NO_SESSION",
      message: "Sign in.",
    });
    await expect(request("/forbidden/")).rejects.toMatchObject({
      status: 403,
      message: "You do not have permission to perform this action.",
    });
  });

  it("normalizes network failures without logging request data", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("socket and secret"));
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    await expect(request("/private/", { method: "POST", body: "secret" })).rejects.toEqual(
      expect.objectContaining({ message: "Network unavailable." }),
    );
    expect(consoleSpy).not.toHaveBeenCalled();
  });

  it("supports successful 204 responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    await expect(api.logout()).resolves.toBeNull();
  });
});
