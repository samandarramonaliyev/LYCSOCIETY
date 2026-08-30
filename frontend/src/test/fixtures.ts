import type { ClubDetail, CurrentUser, Profile } from "../types/api";

export const profile: Profile = {
  first_name: "Sam",
  last_name: "Student",
  lyceum: { id: "lyceum-1", name: "Test Lyceum" },
  group: "10-A",
  about: "About Sam",
  hobbies: "Chess",
  profile_photo_url: "",
  interests: [],
};

export function currentUser(
  overrides: Partial<CurrentUser> = {},
): CurrentUser {
  return {
    account_status: "ACTIVE",
    verification_status: "VERIFIED",
    can_access_student_features: true,
    telegram: { username: "sam", first_name: "Sam", last_name: "Student" },
    profile: {
      about: "",
      hobbies: "",
      profile_photo_url: "",
      interests: [],
    },
    verified_student: {
      first_name: "Sam",
      last_name: "Student",
      lyceum: { id: "lyceum-1", name: "Test Lyceum", code: "test" },
      group: "10-A",
    },
    ...overrides,
  };
}

export function clubDetail(overrides: Partial<ClubDetail> = {}): ClubDetail {
  return {
    id: "club-1",
    name: "Literary Society",
    category: "ARTS",
    short_description: "Read and discuss",
    description: "Long description",
    member_count: 4,
    interests: [],
    owner: {
      first_name: "Owner",
      last_name: "Student",
      about: "",
      profile_photo_url: "",
      interests: [],
    },
    membership_status: null,
    request_status: null,
    request_id: null,
    created_at: "2026-08-30T00:00:00Z",
    ...overrides,
  };
}
