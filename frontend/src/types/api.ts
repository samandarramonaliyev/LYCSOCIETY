export type AuthState =
  | "INITIALIZING"
  | "TELEGRAM_UNAVAILABLE"
  | "AUTHENTICATING"
  | "UNVERIFIED"
  | "VERIFIED"
  | "SUSPENDED"
  | "ERROR";

export type AccountStatus = "ACTIVE" | "SUSPENDED" | "DEACTIVATED";
export type VerificationStatus = "UNVERIFIED" | "VERIFIED" | "SUSPENDED" | "DEACTIVATED";

export interface Interest {
  id: string;
  name: string;
  slug: string;
}

export interface Profile {
  first_name: string | null;
  last_name: string | null;
  lyceum: { id: string; name: string } | null;
  group: string | null;
  about: string;
  hobbies: string;
  profile_photo_url: string;
  interests: Interest[];
}

export interface CurrentUser {
  account_status: AccountStatus;
  verification_status: VerificationStatus;
  can_access_student_features: boolean;
  telegram: { username: string; first_name: string; last_name: string };
  profile: Pick<Profile, "about" | "hobbies" | "profile_photo_url" | "interests">;
  verified_student: {
    first_name: string;
    last_name: string;
    lyceum: { id: string; name: string; code: string };
    group: string;
  } | null;
}

export interface VerificationClaimPayload {
  lyceum_id: string;
  first_name: string;
  last_name: string;
  group: string;
}

export interface ProfileUpdatePayload {
  about?: string;
  hobbies?: string;
  profile_photo_url?: string;
  interest_ids?: string[];
}

export type ClubStatus = "PENDING" | "ACTIVE" | "REJECTED" | "PAUSED" | "ARCHIVED";
export type MembershipRole = "OWNER" | "MEMBER";
export type JoinRequestStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "CANCELLED";

export interface ClubSummary {
  id: string;
  name: string;
  category: string;
  short_description: string;
  member_count: number;
  interests: Interest[];
}

export interface ClubDetail extends ClubSummary {
  description: string;
  owner: {
    first_name: string;
    last_name: string;
    about: string;
    profile_photo_url: string;
    interests: Interest[];
  };
  membership_status: MembershipRole | null;
  request_status: JoinRequestStatus | null;
  request_id: string | null;
  status?: ClubStatus;
  rejection_reason?: string;
  created_at: string;
}

export interface CreateClubPayload {
  name: string;
  short_description: string;
  description: string;
  category: string;
  interest_ids: string[];
}

export interface ClubMember {
  id: string;
  role: MembershipRole;
  joined_at: string;
  student: {
    first_name: string;
    last_name: string;
    group: string;
    profile_photo_url: string;
    interests: Interest[];
  };
}

export interface JoinRequest {
  id: string;
  status: JoinRequestStatus;
  rejection_reason: string;
  created_at: string;
  updated_at: string;
  student: ClubMember["student"] & { about: string };
}

export type MeetingStatus = "SCHEDULED" | "CANCELLED";
export type RSVPStatus = "GOING" | "NOT_GOING";

export interface Meeting {
  id: string;
  title: string;
  description: string;
  starts_at: string;
  location: string;
  status: MeetingStatus;
  created_at: string;
  rsvp?: RSVPStatus;
}

export interface CreateMeetingPayload {
  title: string;
  description: string;
  starts_at: string;
  location: string;
}

export interface MeetingRSVP {
  response: RSVPStatus;
}

export interface Announcement {
  id: string;
  title: string;
  message: string;
  created_at: string;
}

export interface CreateAnnouncementPayload {
  title: string;
  message: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationPreference {
  club_announcements: boolean;
  meeting_notifications: boolean;
  meeting_reminders: boolean;
}

export type ReportReason =
  | "SPAM"
  | "FAKE_INFORMATION"
  | "HARASSMENT"
  | "INAPPROPRIATE"
  | "OTHER";
export type ReportTargetType = "CLUB" | "ANNOUNCEMENT";

export interface CreateReportPayload {
  target_type: ReportTargetType;
  target_id: string;
  reason: ReportReason;
  details?: string;
}

export interface CreateReportResponse {
  id: string;
  status: "OPEN";
}

export interface TelegramGroupStatus {
  linked: boolean;
  title: string;
  status: "LINKED" | "UNLINKED" | "PENDING";
  linked_at: string | null;
}

export interface ApiError {
  code?: string;
  message: string;
  fields?: Record<string, string[]>;
  status?: number;
}
