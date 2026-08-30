import type {
  Announcement,
  ApiError,
  ClubDetail,
  ClubMember,
  ClubSummary,
  CreateAnnouncementPayload,
  CreateClubPayload,
  CreateMeetingPayload,
  CreateReportPayload,
  CreateReportResponse,
  CurrentUser,
  Interest,
  JoinRequest,
  Meeting,
  MeetingRSVP,
  Notification,
  NotificationPreference,
  Profile,
  ProfileUpdatePayload,
  RSVPStatus,
  TelegramGroupStatus,
  VerificationClaimPayload,
} from "../../types/api";

const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api/v1";

function csrfToken(): string {
  const encoded = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1];
  if (!encoded) return "";
  try {
    return decodeURIComponent(encoded);
  } catch {
    return "";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export class ApiClientError extends Error implements ApiError {
  code?: string;
  fields?: Record<string, string[]>;
  status?: number;

  constructor(error: ApiError) {
    super(error.message);
    this.name = "ApiClientError";
    this.code = error.code;
    this.fields = error.fields;
    this.status = error.status;
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const method = (init.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = csrfToken();
    if (token) headers.set("X-CSRFToken", token);
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers,
      credentials: "include",
    });
  } catch {
    throw new ApiClientError({ message: "Network unavailable." });
  }

  const data: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const envelope = isRecord(data) && isRecord(data.error) ? data.error : undefined;
    const legacyMessage = isRecord(data) && typeof data.detail === "string" ? data.detail : undefined;
    throw new ApiClientError({
      message:
        (envelope && typeof envelope.message === "string" ? envelope.message : undefined) ||
        legacyMessage ||
        (response.status === 401
          ? "Your session has expired."
          : response.status === 403
            ? "You do not have permission to perform this action."
            : "Request failed."),
      code: envelope && typeof envelope.code === "string" ? envelope.code : undefined,
      fields:
        envelope && isRecord(envelope.fields)
          ? (envelope.fields as Record<string, string[]>)
          : undefined,
      status: response.status,
    });
  }
  return data as T;
}

export const api = {
  csrf: () => request<{ csrf_token: string }>("/auth/csrf/"),
  authenticate: (init_data: string) =>
    request<{ authenticated: true; csrf_token: string; user: CurrentUser }>("/auth/telegram/", {
      method: "POST",
      body: JSON.stringify({ init_data }),
    }),
  me: () => request<CurrentUser>("/auth/me/"),
  logout: () => request<void>("/auth/logout/", { method: "POST" }),
  lyceums: () => request<{ results: { id: string; name: string; code: string }[] }>("/verification/lyceums/"),
  claim: (data: VerificationClaimPayload) =>
    request<{ user: CurrentUser }>("/verification/claim/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  profile: () => request<Profile>("/profile/"),
  interests: () => request<{ results: Interest[] }>("/interests/"),
  updateProfile: (data: ProfileUpdatePayload) =>
    request<Profile>("/profile/", { method: "PATCH", body: JSON.stringify(data) }),
  clubs: (query = "") => request<{ results: ClubSummary[] }>(`/clubs/${query}`),
  club: (id: string) => request<ClubDetail>(`/clubs/${id}/`),
  mine: () => request<ClubDetail>("/clubs/mine/"),
  createClub: (data: CreateClubPayload) =>
    request<ClubDetail>("/clubs/", { method: "POST", body: JSON.stringify(data) }),
  join: (id: string) =>
    request<JoinRequest>(`/clubs/${id}/join-requests/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  cancel: (id: string) =>
    request<JoinRequest>(`/join-requests/${id}/cancel/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  leave: (id: string) => request<void>(`/clubs/${id}/leave/`, { method: "POST" }),
  members: (id: string) => request<{ results: ClubMember[] }>(`/clubs/${id}/members/`),
  requests: (id: string) => request<{ results: JoinRequest[] }>(`/clubs/${id}/join-requests/`),
  decide: (id: string, action: "accept" | "reject", body: { rejection_reason?: string } = {}) =>
    request<ClubMember | JoinRequest>(`/join-requests/${id}/${action}/`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  resubmit: (id: string) =>
    request<ClubDetail>(`/clubs/${id}/resubmit/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  meetings: (id: string) => request<{ results: Meeting[] }>(`/clubs/${id}/meetings/`),
  meeting: (id: string) => request<Meeting>(`/meetings/${id}/`),
  createMeeting: (id: string, data: CreateMeetingPayload) =>
    request<Meeting>(`/clubs/${id}/meetings/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  cancelMeeting: (id: string) => request<Meeting>(`/meetings/${id}/`, { method: "PATCH" }),
  rsvp: (id: string, response: RSVPStatus) =>
    request<MeetingRSVP>(`/meetings/${id}/rsvp/`, {
      method: "POST",
      body: JSON.stringify({ response }),
    }),
  announcements: (id: string) =>
    request<{ results: Announcement[] }>(`/clubs/${id}/announcements/`),
  createAnnouncement: (id: string, data: CreateAnnouncementPayload) =>
    request<Announcement>(`/clubs/${id}/announcements/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  notifications: () => request<Notification[]>("/notifications/"),
  readNotification: (id: string) =>
    request<Notification>(`/notifications/${id}/read/`, { method: "POST" }),
  preferences: () => request<NotificationPreference>("/notification-preferences/"),
  updatePreferences: (data: Partial<NotificationPreference>) =>
    request<NotificationPreference>("/notification-preferences/", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  telegramStatus: (id: string) => request<TelegramGroupStatus>(`/clubs/${id}/telegram/`),
  telegramStart: (id: string) =>
    request<{ token: string; expires_in: number }>(`/clubs/${id}/telegram/link/start/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  telegramUnlink: (id: string) =>
    request<void>(`/clubs/${id}/telegram/`, { method: "DELETE" }),
  telegramInvite: (id: string) =>
    request<{ invite_link: string }>(`/clubs/${id}/telegram/invite/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  createReport: (data: CreateReportPayload) =>
    request<CreateReportResponse>("/reports/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export const createReport = api.createReport;
